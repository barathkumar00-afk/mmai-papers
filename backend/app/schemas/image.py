"""Schemas for the medical image analysis endpoint."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import (
    EvidenceRef,
    Limitations,
    ModelInfo,
    Provenance,
    Uncertainty,
)


class ImageObservation(BaseModel):
    """A single structured visual observation.

    ``source`` distinguishes what was actually seen from what a model asserted:
    ``"measured"`` (derived from pixel statistics), ``"model_reported"`` (the
    configured VLM stated it) or ``"unavailable"``.
    """

    finding: str = Field(..., min_length=1, max_length=2000)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: str = "model_reported"
    region: Optional[str] = None
    laterality: Optional[str] = None
    severity: Optional[str] = None
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list, description="Supporting observed evidence")
    uncertainty_note: str = ""


class VisualFeature(BaseModel):
    """A named measurable or model-reported visual feature."""

    name: str
    value: Any = None
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    category: str = "morphology"
    measured: bool = Field(True, description="True when computed from pixels in this process")
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    notes: str = ""


class ImageMetadata(BaseModel):
    """Facts about the submitted file, computed locally."""

    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    format: str = ""
    width: int | None = None
    height: int | None = None
    mode: str | None = None
    bit_depth: int | None = None
    frames: int | None = None
    photometric_interpretation: str | None = None
    modality: str | None = None
    is_dicom: bool = False
    de_identified: bool = Field(False, description="True if DICOM tags were stripped")


class ImageAnalysisRequest(BaseModel):
    """JSON-body variant of the image request (base64 / DICOM windowing)."""

    dicom_b64: Optional[str] = Field(None, description="Base64 DICOM payload")
    filename: str = "upload.dcm"
    window_level: Optional[List[float]] = Field(
        None, description="Optional [center, width] DICOM windowing applied before analysis"
    )
    de_identify: bool = Field(True, description="Strip DICOM patient tags before processing")
    modality_hint: Optional[str] = Field(None, description="e.g. 'cxr' or 'ct'")

    @field_validator("window_level")
    @classmethod
    def _validate_window(cls, value: Optional[List[float]]) -> Optional[List[float]]:
        if value is None:
            return None
        if len(value) != 2:
            raise ValueError("window_level must be a [center, width] pair")
        if value[1] <= 0:
            raise ValueError("window_level width must be positive")
        return value


class ImageAnalysisResponse(BaseModel):
    success: bool = True
    modality: str = Field(..., description="Detected or requested modality, e.g. 'chest_xray'")
    observations: List[ImageObservation] = Field(default_factory=list)
    visual_features: List[VisualFeature] = Field(default_factory=list)
    evidence_regions: List[EvidenceRef] = Field(default_factory=list)
    uncertainty: Uncertainty
    model: ModelInfo
    limitations: List[Limitations] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    metadata: ImageMetadata
    provenance: Provenance
    request_id: str = ""
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
