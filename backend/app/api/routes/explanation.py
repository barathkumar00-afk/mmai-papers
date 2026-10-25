"""``POST /api/generate/explanation`` -- auditable evidence trail."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter

from app.api.routes.deps import parse_int
from app.core.logging import get_logger
from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.services.case_store import case_store
from app.services.explanation_service import explanation_service

router = APIRouter(tags=["Explainability"])
logger = get_logger(__name__)

_ALLOWED_MODALITIES = {"image", "speech", "clinical"}


@router.post(
    "/explanation",
    response_model=ExplanationResponse,
    summary="Generate the evidence trail and per-modality contribution breakdown",
)
async def generate_explanation(request: ExplanationRequest) -> ExplanationResponse:
    started = time.perf_counter()
    rid = uuid.uuid4().hex[:12]

    analysis = case_store.get(request.case_id) if request.case_id else None
    if request.case_id and analysis is None:
        logger.info("explanation_case_not_found", extra={"case_id": request.case_id})

    modalities = [m.strip().lower() for m in request.modalities if m.strip().lower() in _ALLOWED_MODALITIES]
    if not modalities:
        modalities = ["image", "speech", "clinical"]

    return await explanation_service.explain(
        analysis=analysis,
        query=request.query,
        top_k=parse_int(str(request.top_k) if request.top_k else None, "top_k", 5, low=1, high=25),
        modalities=modalities,
        request_id=rid,
    )
