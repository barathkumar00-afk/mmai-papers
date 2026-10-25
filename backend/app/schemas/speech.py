"""Schemas for the speech / audio analysis endpoint."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import Limitations, ModelInfo, Provenance, Uncertainty


class ClinicalObservation(BaseModel):
    """A statement extractable from the transcript.

    ``source`` is one of ``"transcript"`` (directly stated by the patient),
    ``"acoustic"`` (derived from measurable audio characteristics) or
    ``"unavailable"``. Symptoms are never added beyond what is present.
    """

    observation: str = Field(..., min_length=1, max_length=2000)
    category: str = "symptom"
    source: str = "transcript"
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, description="Verbatim transcript spans")
    time_span_seconds: Optional[List[float]] = None
    uncertainty_note: str = ""


class SpeechFeature(BaseModel):
    """A measurable or model-reported acoustic feature."""

    name: str
    value: Any = None
    unit: str = ""
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    measured: bool = True
    category: str = "acoustic"
    notes: str = ""


class TranscriptSegment(BaseModel):
    start: float = 0.0
    end: float = 0.0
    text: str = ""


class SpeechMetadata(BaseModel):
    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    format: str = ""
    duration_seconds: Optional[float] = None
    sample_rate_hz: Optional[int] = None
    channels: Optional[int] = None
    resampled_to_hz: Optional[int] = None
    rms_dbfs: Optional[float] = None
    peak_dbfs: Optional[float] = None
    silence_ratio: Optional[float] = None
    clipped_ratio: Optional[float] = None


class SpeechAnalysisRequest(BaseModel):
    """JSON-body variant (base64 audio)."""

    audio_clip_wav_b64: Optional[str] = None
    filename: str = "clip.wav"
    sample_rate_hz: Optional[int] = Field(None, description="Expected source sample rate, for reporting only")
    language: Optional[str] = Field(None, description="Hint passed through to the ASR model")


class SpeechAnalysisResponse(BaseModel):
    success: bool = True
    transcript: str = ""
    segments: List[TranscriptSegment] = Field(default_factory=list)
    clinical_observations: List[ClinicalObservation] = Field(default_factory=list)
    speech_features: List[SpeechFeature] = Field(default_factory=list)
    uncertainty: Uncertainty
    model: ModelInfo
    limitations: List[Limitations] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    metadata: SpeechMetadata
    provenance: Provenance
    request_id: str = ""
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
