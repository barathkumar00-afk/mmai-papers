"""``GET /api/health`` -- service, model and retrieval availability.

Never raises, never exposes secrets, and never blocks: unavailable dependencies
are reported as data.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.services.retrieval_service import faiss_available, retrieval_service
from app.utils import audio_utils, image_utils

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get("", summary="Service and dependency health")
async def health_check() -> JSONResponse:
    settings = get_settings()

    ollama_status = await llm_service.availability()

    retrieval_state = retrieval_service.status()
    if not retrieval_state.get("initialized"):
        retrieval_service.load()
        retrieval_state = retrieval_service.status()

    retrieval_payload: Dict[str, Any] = {
        "available": bool(retrieval_state.get("initialized")) and faiss_available(),
        "index_initialized": bool(retrieval_state.get("initialized")),
        "index_path": str(settings.FAISS_INDEX_PATH),
        "total_documents": retrieval_state.get("total_documents", 0),
        "total_chunks": retrieval_state.get("total_chunks", 0),
        "dimension": retrieval_state.get("dimension", 0),
        "similarity_metric": retrieval_state.get("similarity_metric", "cosine"),
        "faiss_installed": faiss_available(),
        "encoder": embedding_service.info().model_dump(),
        "message": None if retrieval_state.get("initialized") else "Knowledge base not initialized",
    }

    speech_model = settings.WHISPER_MODEL_PATH or "(not configured)"
    vision_model = settings.OLLAMA_VISION_MODEL or "(not configured)"

    payload: Dict[str, Any] = {
        "status": "online",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "mock_mode": settings.MOCK_MODE,
        "ollama": ollama_status,
        "retrieval": retrieval_payload,
        "models": {
            "llm": {
                "name": settings.OLLAMA_LLM_MODEL,
                "status": "simulated" if settings.MOCK_MODE else ollama_status.get("status", "unknown"),
                "source": "ollama",
            },
            "vision": {
                "name": vision_model,
                "status": "simulated" if settings.MOCK_MODE else ("configured" if settings.OLLAMA_VISION_MODEL else "unconfigured"),
                "source": "ollama",
            },
            "speech": {
                "name": speech_model,
                "status": "simulated" if settings.MOCK_MODE else ("configured" if settings.WHISPER_MODEL_PATH else "unconfigured"),
                "source": "local_whisper",
            },
            "embedding": embedding_service.info().model_dump(),
            "fusion": {
                "name": "MedExplainFusionService",
                "role": "integration_layer",
                "status": "integration_layer",
                "is_trained_neural_fusion_model": False,
                "note": "Integration/prototype fusion layer over per-modality representations; not a newly trained cross-attention network.",
            },
        },
        "dependencies": {
            "pillow": image_utils.PIL_AVAILABLE,
            "numpy": image_utils.NUMPY_AVAILABLE,
            "pydicom": image_utils.DICOM_AVAILABLE,
            "soundfile": audio_utils.SOUNDFILE_AVAILABLE,
            "librosa": audio_utils.LIBROSA_AVAILABLE,
            "ffmpeg": audio_utils.ffmpeg_available(),
        },
        "limits": {
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "allowed_image_extensions": settings.ALLOWED_IMAGE_EXTENSIONS,
            "allowed_audio_extensions": settings.ALLOWED_AUDIO_EXTENSIONS,
        },
        "clinical_positioning": {
            "autonomous_diagnosis": False,
            "human_review_required": True,
            "notice": settings.HUMAN_REVIEW_NOTICE,
        },
        "documentation": "/docs",
    }

    return JSONResponse(status_code=200, content=payload)


@router.get("/ready", summary="Dependency readiness detail")
async def readiness() -> JSONResponse:
    """Verbose readiness probe for operators. Same data as /health plus notes."""
    response = await health_check()
    body: Dict[str, Any] = response.body  # type: ignore[assignment]
    import json

    payload = json.loads(body) if isinstance(body, (bytes, bytearray)) else body
    notes: List[str] = []
    if not payload.get("ollama", {}).get("available"):
        notes.append(
            "Ollama is unreachable. Set MOCK_MODE=true to run the API without local models."
        )
    if payload.get("retrieval", {}).get("message"):
        notes.append(
            "Run `python -m scripts.ingest_knowledge` (or POST /api/retrieve/ingest) to build the index."
        )
    if not payload.get("models", {}).get("vision", {}).get("name", "").strip("()"):
        notes.append("Set OLLAMA_VISION_MODEL to enable visual-language analysis.")
    if not payload.get("models", {}).get("speech", {}).get("name", "").strip("()"):
        notes.append("Set WHISPER_MODEL_PATH to enable local speech recognition.")
    payload["notes"] = notes
    payload["ready"] = bool(notes) is False
    return JSONResponse(status_code=200, content=payload)
