"""``POST /api/generate/report`` -- structured clinical decision-support report."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.report import ReportRequest, ReportResponse
from app.services.case_store import case_store
from app.services.report_service import report_service

router = APIRouter(tags=["Reporting"])
logger = get_logger(__name__)


@router.post(
    "/report",
    response_model=ReportResponse,
    summary="Generate the 14-section clinical decision-support report",
)
async def generate_report(request: ReportRequest) -> ReportResponse:
    started = time.perf_counter()
    rid = uuid.uuid4().hex[:12]

    analysis = case_store.get(request.case_id) if request.case_id else None
    if request.case_id and analysis is None:
        logger.info("report_case_not_found", extra={"case_id": request.case_id})

    return await report_service.generate(
        analysis=analysis,
        case_id=request.case_id,
        query=request.query,
        top_k=max(1, min(request.top_k, 25)),
        include_sections=request.include_sections or None,
        request_id=rid,
    )
