"""``POST /api/analyze/speech`` -- structured analysis of a clinical audio clip."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, File, Form, UploadFile

from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.speech import SpeechAnalysisRequest, SpeechAnalysisResponse
from app.api.routes.deps import read_validated_upload
from app.services.speech_service import speech_service
from app.utils.image_utils import decode_base64_image

router = APIRouter(tags=["Analysis"])
logger = get_logger(__name__)


@router.post(
    "/speech",
    response_model=SpeechAnalysisResponse,
    summary="Transcribe and analyze a clinical audio clip",
)
async def analyze_speech(
    file: Optional[UploadFile] = File(None, description="Audio file: .wav/.mp3/.m4a/.flac/.ogg"),
    language: Optional[str] = Form(None, description="ISO language code hint for the ASR model"),
    request: Optional[SpeechAnalysisRequest] = Body(None, include_in_body=False),
) -> SpeechAnalysisResponse:
    data: Optional[bytes] = None
    filename = "clip.wav"
    lang = language

    if file is not None and file.filename:
        data = await read_validated_upload(file, kind="audio")
        filename = file.filename or filename
    elif request is not None and request.audio_clip_wav_b64:
        data = decode_base64_image(request.audio_clip_wav_b64)  # identical base64 decode path
        filename = request.filename or filename
        lang = lang or request.language

    if not data:
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "No audio was supplied. Send a multipart 'file' field or a JSON body with "
            "'audio_clip_wav_b64'.",
            status_code=400,
        )

    return await speech_service.analyze(data, filename=filename, language=lang)
