"""``POST /api/analyze/image`` -- structured medical image analysis.

Accepts either a multipart file upload or a JSON body carrying base64 DICOM.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, File, Form, UploadFile

from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.image import ImageAnalysisRequest, ImageAnalysisResponse
from app.api.routes.deps import (
    parse_bool,
    parse_float_list,
    read_validated_upload,
)
from app.services.vision_service import vision_service
from app.utils.image_utils import decode_base64_image

router = APIRouter(tags=["Analysis"])
logger = get_logger(__name__)


@router.post(
    "/image",
    response_model=ImageAnalysisResponse,
    summary="Analyze a medical image (PNG/JPEG/DICOM)",
)
async def analyze_image(
    file: Optional[UploadFile] = File(None, description="Image file: .png/.jpg/.jpeg/.dcm"),
    modality_hint: Optional[str] = Form(None, description="e.g. 'cxr' or 'ct'"),
    focus: Optional[str] = Form(None, description="Region of interest hint for the VLM"),
    window_level: Optional[str] = Form(
        None, description="DICOM windowing as a JSON array [center, width]"
    ),
    de_identify: Optional[str] = Form("true", description="Strip DICOM patient identifiers"),
    request: Optional[ImageAnalysisRequest] = Body(None, include_in_body=False),
) -> ImageAnalysisResponse:
    data: Optional[bytes] = None
    filename = "upload.dcm"
    hint = modality_hint
    focus_text = focus
    window = parse_float_list(window_level, "window_level")
    deidentify = parse_bool(de_identify, True)

    if file is not None and file.filename:
        data = await read_validated_upload(file, kind="image")
        filename = file.filename or filename
    elif request is not None and request.dicom_b64:
        data = decode_base64_image(request.dicom_b64)
        filename = request.filename or filename
        hint = hint or request.modality_hint
        window = window or request.window_level
        deidentify = request.de_identify

    if not data:
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "No image was supplied. Send a multipart 'file' field or a JSON body with 'dicom_b64'.",
            status_code=400,
        )

    return await vision_service.analyze(
        data,
        filename=filename,
        modality_hint=hint,
        window_level=window,
        de_identify=deidentify,
        focus=focus_text,
    )
