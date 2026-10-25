"""Shared route helpers: upload validation and multimodal request parsing."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from fastapi import Form, UploadFile

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.security import read_upload_limited, validate_upload
from app.schemas.clinical import ClinicalInput

logger = get_logger(__name__)


async def read_validated_upload(
    upload: Optional[UploadFile],
    *,
    kind: str,
) -> Optional[bytes]:
    """Read and validate an optional upload. Returns ``None`` when absent.

    Raises :class:`AppError` with a precise code for empty, oversized, corrupt or
    unsupported files. The payload is read with a hard byte cap so an oversized
    body is rejected before it is fully buffered.
    """
    if upload is None:
        return None
    settings = get_settings()
    if not upload.filename and not getattr(upload, "_rolled", True):
        return None

    data = await read_upload_limited(upload.file, settings.max_upload_bytes)
    if not data:
        return None

    if kind == "image":
        validate_upload(
            filename=upload.filename,
            data=data,
            allowed_extensions=settings.ALLOWED_IMAGE_EXTENSIONS,
            content_prefix="image",
        )
    else:
        validate_upload(
            filename=upload.filename,
            data=data,
            allowed_extensions=settings.ALLOWED_AUDIO_EXTENSIONS,
            content_prefix="audio",
        )
    return data


def parse_json_field(raw: Optional[str], field: str) -> Any:
    """Parse an optional JSON form field, raising a clear error when malformed."""
    if raw is None or not str(raw).strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError(
            ErrorCode.MALFORMED_CLINICAL_DATA,
            f"Field '{field}' must be valid JSON.",
            status_code=400,
            details={"position": exc.pos},
        ) from exc


def parse_float_list(raw: Optional[str], field: str) -> Optional[List[float]]:
    """Parse ``[center, width]`` from a JSON array or a comma-separated string."""
    value = parse_json_field(raw, field) if raw and str(raw).strip().startswith("[") else raw
    if value is None:
        return None
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]
    elif isinstance(value, (list, tuple)):
        parts = [str(p) for p in value]
    else:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Field '{field}' must be a two-element numeric array.",
            status_code=400,
        )
    try:
        numbers = [float(p) for p in parts]
    except ValueError as exc:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, f"Field '{field}' must contain numbers.", status_code=400
        ) from exc
    if len(numbers) != 2:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Field '{field}' must contain exactly two values.",
            status_code=400,
        )
    return numbers


def parse_bool(raw: Optional[str], default: bool = False) -> bool:
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def parse_float(raw: Optional[str], field: str, default: Optional[float] = None) -> Optional[float]:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return float(str(raw).strip())
    except ValueError as exc:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, f"Field '{field}' must be a number.", status_code=400
        ) from exc


def parse_int(raw: Optional[str], field: str, default: int, *, low: int = 1, high: int = 50) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(float(str(raw).strip()))
    except ValueError as exc:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, f"Field '{field}' must be an integer.", status_code=400
        ) from exc
    return max(low, min(high, value))


def parse_weights(raw: Optional[str]) -> Dict[str, float]:
    """Parse optional modality weights; ignores unknown keys and non-numbers."""
    parsed = parse_json_field(raw, "weights")
    if not isinstance(parsed, dict):
        return {}
    allowed = {"image", "speech", "clinical", "ehr", "text"}
    weights: Dict[str, float] = {}
    for key, value in parsed.items():
        name = str(key).strip().lower()
        if name not in allowed:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        weights[name] = max(0.0, min(number, 1.0))
    return weights


async def build_clinical_input(
    *,
    symptoms: Optional[str] = None,
    history: Optional[str] = None,
    medications: Optional[str] = None,
    clinical_notes: Optional[str] = None,
    chief_complaint: Optional[str] = None,
    complaint: Optional[str] = None,
    vitals: Optional[str] = None,
    labs: Optional[str] = None,
    spo2: Optional[str] = None,
    crp: Optional[str] = None,
    comorbidities: Optional[str] = None,
) -> ClinicalInput:
    """Assemble a :class:`ClinicalInput` from multipart form fields.

    Accepts both the workbench's simple strings and richer JSON payloads.
    """
    return ClinicalInput(
        symptoms=_as_list(symptoms),
        history=_as_list(history),
        medications=_as_list(medications),
        clinical_notes=(clinical_notes or "")[: get_settings().MAX_CLINICAL_TEXT_CHARS],
        chief_complaint=chief_complaint or "",
        complaint=complaint or "",
        vitals=parse_json_field(vitals, "vitals") or {},
        labs=parse_json_field(labs, "labs") or {},
        spo2=spo2 or "",
        crp=crp or "",
        comorbidities=comorbidities or "",
    )


def _as_list(value: Optional[str]) -> List[str]:
    if not value or not str(value).strip():
        return []
    parsed = None
    stripped = str(value).strip()
    if stripped.startswith("["):
        parsed = parse_json_field(stripped, "list")
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        return [f"{k}: {v}" for k, v in parsed.items()]
    return [part.strip() for part in stripped.replace("\n", ";").split(";") if part.strip()]


def require_at_least_one(values: Iterable[Optional[Any]]) -> None:
    if not any(bool(value) and str(value).strip() for value in values if value is not None):
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "Provide at least one of: symptoms, vitals, labs, clinical_notes, complaint.",
            status_code=400,
        )
