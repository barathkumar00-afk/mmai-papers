"""``POST /api/analyze/multimodal`` -- the main orchestration pipeline.

Accepts image and/or audio uploads together with structured clinical input, runs
the full chain (per-modality analysis -> integration fusion -> retrieval ->
grounded RAG reasoning -> evidence trace) and returns a response shaped for the
existing workbench UI.

A completed analysis is cached for ``CASE_TTL_SECONDS`` so that
``/api/generate/explanation`` and ``/api/generate/report`` can reference it by
``case_id``.
"""

from __future__ import annotations

import base64
import binascii
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from app.api.routes.deps import (
    build_clinical_input,
    parse_bool,
    parse_float_list,
    parse_int,
    parse_weights,
    read_validated_upload,
)
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.multimodal import MultimodalAnalysisResponse
from app.services.case_store import case_store
from app.services.fusion_service import multimodal_fusion_service
from app.utils.image_utils import decode_base64_image

router = APIRouter(tags=["Analysis"])
logger = get_logger(__name__)


def _decode_b64_field(value: Optional[str], field: str) -> Optional[bytes]:
    if not value or not value.strip():
        return None
    try:
        return decode_base64_image(value)
    except AppError as exc:
        raise AppError(exc.code, f"Field '{field}': {exc.message}", status_code=exc.status_code) from exc


@router.post(
    "/multimodal",
    response_model=MultimodalAnalysisResponse,
    summary="Run the full multimodal clinical decision-support pipeline",
)
async def analyze_multimodal(
    image: Optional[UploadFile] = File(None, description="Medical image (optional)"),
    audio: Optional[UploadFile] = File(None, description="Clinical audio clip (optional)"),
    case_id: str = Form("#MED-2025-0941"),
    patient_id: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    history: Optional[str] = Form(None),
    medications: Optional[str] = Form(None),
    clinical_notes: Optional[str] = Form(None),
    chief_complaint: Optional[str] = Form(None),
    complaint: Optional[str] = Form(None, description="Workbench field: complaint / timeline"),
    vitals: Optional[str] = Form(None),
    labs: Optional[str] = Form(None),
    spo2: Optional[str] = Form(None, description="Workbench field: SpO2"),
    crp: Optional[str] = Form(None, description="Workbench field: CRP mg/L"),
    comorbidities: Optional[str] = Form(None, description="Workbench field: comorbidity summary"),
    image_modality_hint: Optional[str] = Form(None, description="'cxr' or 'ct'"),
    image_focus: Optional[str] = Form(None, description="Region-of-interest hint for the vision model"),
    image_dicom_b64: Optional[str] = Form(None, description="Base64 DICOM as an alternative to the file field"),
    audio_b64: Optional[str] = Form(None, description="Base64 WAV as an alternative to the file field"),
    window_level: Optional[str] = Form(None, description="DICOM windowing [center, width]"),
    de_identify: Optional[str] = Form("true"),
    weights: Optional[str] = Form(None, description="JSON object of advisory modality weights"),
    top_k: Optional[str] = Form(None, description="Number of retrieved evidence chunks (1-25)"),
    include_report: Optional[str] = Form("false"),
    request_explanation: Optional[str] = Form("false"),
) -> MultimodalAnalysisResponse:
    image_data = await read_validated_upload(image, kind="image")
    audio_data = await read_validated_upload(audio, kind="audio")

    if not image_data:
        image_data = _decode_b64_field(image_dicom_b64, "image_dicom_b64")
    if not audio_data:
        audio_data = _decode_b64_field(audio_b64, "audio_b64")

    clinical = await build_clinical_input(
        symptoms=symptoms,
        history=history,
        medications=medications,
        clinical_notes=clinical_notes,
        chief_complaint=chief_complaint,
        complaint=complaint,
        vitals=vitals,
        labs=labs,
        spo2=spo2,
        crp=crp,
        comorbidities=comorbidities,
    )

    has_clinical = bool(
        clinical.all_text().strip() or clinical.labs or clinical.vitals or clinical.spo2 or clinical.crp
    )
    if not image_data and not audio_data and not has_clinical:
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "At least one input is required: an image file, an audio file, or clinical data "
            "(symptoms / vitals / labs / complaint).",
            status_code=400,
        )

    result = await multimodal_fusion_service.analyze(
        image_data=image_data,
        image_filename=(image.filename if image and image.filename else "upload.dcm"),
        image_modality_hint=image_modality_hint,
        image_focus=image_focus,
        window_level=parse_float_list(window_level, "window_level"),
        de_identify=parse_bool(de_identify, True),
        audio_data=audio_data,
        audio_filename=(audio.filename if audio and audio.filename else "clip.wav"),
        clinical=clinical if has_clinical else None,
        case_id=case_id or "#MED-2025-0941",
        top_k=parse_int(top_k, "top_k", 5, low=1, high=25),
        weights=parse_weights(weights),
    )

    case_store.put(case_id or result.case_id, result)

    # Optional convenience attachments, produced from the cached analysis.
    if parse_bool(include_report, False):
        from app.services.report_service import report_service

        report = await report_service.generate(analysis=result, case_id=result.case_id)
        result.report = {
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "summary": report.summary,
            "sections": [section.model_dump() for section in report.sections],
            "safety_disclaimer": report.safety_disclaimer,
            "human_review_required": report.human_review_required,
        }

    if parse_bool(request_explanation, False):
        from app.services.explanation_service import explanation_service

        explanation = await explanation_service.explain(analysis=result)
        result.explanation = explanation.model_dump()

    return result
