"""MedExplain AI backend application factory.

Startup sequence
----------------
1. Load configuration from the environment / ``.env``.
2. Configure structured logging.
3. Ensure runtime directories exist.
4. Attempt to load the FAISS index (best effort -- never fatal).
5. Install CORS, exception handlers and request-ID middleware.

The API starts and stays up even when Ollama, FAISS, a vision model or a speech
model is missing. Unavailability is reported through ``/api/health`` and through
per-response metadata, never through a crash.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import router as api_router
from app.core.config import ensure_directories, get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import configure_logging, get_logger
from app.services.retrieval_service import retrieval_service

logger = get_logger(__name__)

DESCRIPTION = """
Explainable Multimodal Clinical Intelligence -- **AI-assisted clinical decision
support** for a research prototype.

**Clinical safety**

* This service does **not** perform autonomous diagnosis.
* It does **not** replace a qualified healthcare professional.
* Every reasoning response carries a human-review requirement.
* No accuracy, sensitivity, specificity, F1, AUC or hallucination-rate figure is
  produced: none has been measured for this system.
* No medical citation is ever fabricated. When the knowledge base is empty, the
  API says `Knowledge base not initialized` and returns no evidence.

**Fusion layer transparency**

The multimodal fusion component is an *integration / prototype* layer that
combines structured per-modality representations. It is **not** a trained
cross-attention or latent-alignment neural network, and no attention weights are
reported. See `GET /api/health` -> `models.fusion`.
"""

TAGS_METADATA = [
    {"name": "Health", "description": "Service and dependency availability."},
    {"name": "Image Analysis", "description": "Structured analysis of a medical image."},
    {"name": "Speech Analysis", "description": "Transcript and acoustic analysis of a clinical clip."},
    {"name": "Clinical Analysis", "description": "Normalization of clinical text into a structured record."},
    {"name": "Multimodal", "description": "The full decision-support pipeline."},
    {"name": "Retrieval", "description": "FAISS evidence retrieval and knowledge-base ingestion."},
    {"name": "Explainability", "description": "Auditable evidence trail and contribution breakdown."},
    {"name": "Reporting", "description": "14-section clinical decision-support report."},
    {"name": "v2 Compatibility", "description": "Contracts documented by the existing frontend."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    ensure_directories()
    logger.info(
        "startup",
        extra={
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "mock_mode": settings.MOCK_MODE,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "llm_model": settings.OLLAMA_LLM_MODEL,
            "vision_model": settings.OLLAMA_VISION_MODEL or None,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
        },
    )
    loaded = retrieval_service.load()
    logger.info("retrieval_index", extra={"loaded": loaded, **retrieval_service.status()})
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description=DESCRIPTION,
        version=settings.APP_VERSION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ------------------------------------------------------------------ CORS
    # Explicit origin list from configuration. Wildcards are never used with
    # credentials, which keeps the clinical workflow free of CSRF exposure.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
        max_age=600,
    )

    # ------------------------------------------------------------- middleware
    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except AppError:
            raise
        except Exception:
            logger.exception(
                "unhandled_exception",
                extra={"path": request.url.path, "method": request.method, "request_id": request_id},
            )
            response = _error_response(
                ErrorCode.INTERNAL_ERROR,
                "An internal error occurred.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                request_id,
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
        return response

    # ------------------------------------------------------ exception handlers
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            extra={
                "code": exc.code,
                "status": exc.status_code,
                "path": request.url.path,
                "detail": exc.message,
            },
        )
        payload = exc.to_payload()
        payload["error"].setdefault("details", {})
        if settings.is_production:
            payload["error"].pop("details", None)
        payload["request_id"] = getattr(request.state, "request_id", "")
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "validation_error",
            extra={"path": request.url.path, "error_count": len(exc.errors())},
        )
        request_id = getattr(request.state, "request_id", "")
        if settings.is_production:
            details: Dict[str, Any] = {}
        else:
            details = {
                "errors": [
                    {
                        "field": ".".join(str(part) for part in error.get("loc", [])[1:]) or "body",
                        "message": error.get("msg", ""),
                        "type": error.get("type", ""),
                    }
                    for error in exc.errors()[:10]
                ]
            }
        payload = {
            "success": False,
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": "Request validation failed.",
                "details": details,
            },
            "request_id": request_id,
        }
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = {
            400: ErrorCode.MALFORMED_CLINICAL_DATA,
            404: ErrorCode.MISSING_PARAMETER,
            413: ErrorCode.FILE_TOO_LARGE,
            415: ErrorCode.UNSUPPORTED_FORMAT,
            422: ErrorCode.VALIDATION_ERROR,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        logger.warning(
            "http_error", extra={"path": request.url.path, "status": exc.status_code}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": code,
                    "message": str(exc.detail) if exc.status_code < 500 else "An internal error occurred.",
                },
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path, "request_id": getattr(request.state, "request_id", "")},
        )
        return _error_response(
            ErrorCode.INTERNAL_ERROR,
            "An internal error occurred." if settings.is_production else f"{type(exc).__name__}: {exc}",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            getattr(request.state, "request_id", ""),
        )

    # ---------------------------------------------------------------- routes
    app.include_router(api_router, prefix="/api")

    @app.get("/", tags=["Health"], summary="Service banner")
    async def root() -> Dict[str, Any]:
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "documentation": "/docs",
            "health": "/api/health",
            "clinical_positioning": "AI-assisted clinical decision support. "
            "Not an autonomous diagnosis. Requires review by a qualified healthcare professional.",
        }

    return app


def _error_response(code: str, message: str, status_code: int, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message},
            "request_id": request_id,
        },
    )


app = create_app()
