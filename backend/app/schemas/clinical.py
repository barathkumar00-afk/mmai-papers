"""Schemas for the structured clinical text endpoint."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.schemas.common import Limitations, ModelInfo, Provenance, Uncertainty

_NUM_RE = re.compile(r"[-+]?\d*\.?\d+")
_UNIT_MAP = {
    "spo2": "percent",
    "sao2": "percent",
    "crp": "mg/L",
    "pct": "mg/L",
    "hb": "g/dL",
    "hemoglobin": "g/dL",
    "wbc": "10^3/uL",
    "platelets": "10^3/uL",
    "plts": "10^3/uL",
    "hr": "bpm",
    "heart_rate": "bpm",
    "sbp": "mmHg",
    "dbp": "mmHg",
    "rr": "breaths/min",
    "resp_rate": "breaths/min",
    "temp": "celsius",
    "temperature": "celsius",
    "pao2": "mmHg",
    "fio2": "ratio",
    "bnp": "pg/mL",
    "troponin": "ng/mL",
    "inr": "ratio",
    "creatinine": "mg/dL",
    "lactate": "mmol/L",
    "ph": "pH",
}


def _max_len() -> int:
    try:
        return get_settings().MAX_CLINICAL_TEXT_CHARS
    except Exception:  # pragma: no cover - settings unavailable at import time
        return 20000


def _clean_list(values: Optional[List[str]], limit: int = 100) -> List[str]:
    if not values:
        return []
    out: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out.append(text[:500])
        if len(out) >= limit:
            break
    return out


class VitalSign(BaseModel):
    name: str
    raw: str = ""
    value: Optional[float] = None
    unit: str = ""
    reference_range: Optional[List[float]] = None
    abnormal: Optional[bool] = None
    direction: Optional[str] = Field(None, description="'high' | 'low' | 'normal' | 'unknown'")
    note: str = ""

    model_config = {"protected_namespaces": ()}


class LabValue(BaseModel):
    name: str
    raw: str = ""
    value: Optional[float] = None
    unit: str = ""
    reference_range: Optional[List[float]] = None
    abnormal: Optional[bool] = None
    direction: Optional[str] = None
    source: str = "reported"

    model_config = {"protected_namespaces": ()}


class ClinicalFeature(BaseModel):
    """A derived, deterministic flag (e.g. 'room_air_hypoxemia')."""

    name: str
    detail: str = ""
    inputs: List[str] = Field(default_factory=list)
    rule: str = Field("", description="Human-readable rule that fired")
    confidence: float = 0.9
    simulated: bool = False


class ClinicalInput(BaseModel):
    """Accepts both the workbench UI fields and a richer structured payload.

    The workbench sends ``spo2``/``crp``/``complaint``/``comorbidities`` as form
    fields, so those are the primary fields. Everything else is optional.
    """

    model_config = {"extra": "allow"}

    symptoms: List[str] = Field(default_factory=list)
    history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    clinical_notes: str = ""
    chief_complaint: str = ""
    complaint: str = Field("", description="Workbench field: chief complaint / timeline")
    vitals: Dict[str, str] = Field(default_factory=dict)
    labs: Dict[str, Any] = Field(default_factory=dict)

    # Workbench-compatible convenience fields
    spo2: str = Field("", description="Oxygen saturation, e.g. '88% (Ambient Air)'")
    crp: str = Field("", description="C-reactive protein in mg/L, e.g. '42.4'")
    comorbidities: str = Field("", description="Free-text comorbidity summary")

    @field_validator("symptoms", "history", "medications", mode="before")
    @classmethod
    def _normalize_list(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"[;\n]+", value)
            return _clean_list(parts)
        if isinstance(value, dict):
            return _clean_list([f"{k}: {v}" for k, v in value.items()])
        return _clean_list(value)

    @field_validator("clinical_notes", "chief_complaint", "complaint", "comorbidities", mode="before")
    @classmethod
    def _coerce_text(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        if not isinstance(value, str):
            return str(value)
        limit = _max_len()
        return value.strip()[:limit]

    @field_validator("vitals", "labs", mode="before")
    @classmethod
    def _coerce_mapping(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}
        if isinstance(value, str):
            # Accept a compact "name: value" or JSON-encoded mapping.
            stripped = value.strip()
            if stripped.startswith("{"):
                import json

                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        return {str(k): v for k, v in parsed.items()}
                except json.JSONDecodeError:
                    pass
            pairs: Dict[str, Any] = {}
            for item in re.split(r"[;\n]", stripped):
                if ":" in item:
                    key, _, val = item.partition(":")
                    pairs[key.strip()] = val.strip()
            return pairs
        return {}

    def all_text(self) -> str:
        """Flatten the record into narrative text for retrieval/LLM prompting."""
        parts: List[str] = []
        if self.complaint:
            parts.append(self.complaint)
        if self.chief_complaint:
            parts.append(self.chief_complaint)
        if self.symptoms:
            parts.append("Symptoms: " + ", ".join(self.symptoms))
        if self.history:
            parts.append("History: " + ", ".join(self.history))
        if self.medications:
            parts.append("Medications: " + ", ".join(self.medications))
        if self.comorbidities:
            parts.append(f"Comorbidities: {self.comorbidities}")
        if self.labs:
            parts.append(
                "Labs: " + ", ".join(f"{k}={v}" for k, v in self.labs.items())
            )
        if self.vitals:
            parts.append(
                "Vitals: " + ", ".join(f"{k}={v}" for k, v in self.vitals.items())
            )
        if self.clinical_notes:
            parts.append("Clinical notes: " + self.clinical_notes)
        return "\n".join(parts)


class ClinicalAnalysisResponse(BaseModel):
    success: bool = True
    patient_representation: Dict[str, Any] = Field(default_factory=dict)
    normalized_data: Dict[str, Any] = Field(default_factory=dict)
    symptoms: List[str] = Field(default_factory=list)
    history: List[str] = Field(default_factory=list)
    labs: Dict[str, Any] = Field(default_factory=dict)
    vitals: Dict[str, Any] = Field(default_factory=dict)
    medications: List[str] = Field(default_factory=list)
    clinical_features: List[ClinicalFeature] = Field(default_factory=list)
    retrieval_query: str = ""
    uncertainty: Uncertainty
    model: ModelInfo
    limitations: List[Limitations] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    provenance: Provenance
    request_id: str = ""
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
