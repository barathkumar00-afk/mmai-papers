"""Schemas for the structured clinical decision-support report."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import (
    Limitations,
    ModelInfo,
    Provenance,
    SafetyNotice,
    StageTiming,
    Uncertainty,
)


class ReportSection(BaseModel):
    """One numbered section of the clinical dossier."""

    number: int
    key: str
    title: str
    content: Any = Field(..., description="String, list of strings, or structured object")
    is_populated: bool = True
    provenance: str = "observed"  # observed | retrieved | model_generated | none
    note: str = ""


class ReportRequest(BaseModel):
    case_id: Optional[str] = None
    query: str = ""
    include_sections: List[str] = Field(
        default_factory=list, description="Optional subset of section keys; empty means all"
    )
    top_k: int = 5
    format: str = Field("json", pattern="^(json|text)$")


class ReportResponse(BaseModel):
    success: bool = True
    report_id: str = ""
    case_id: Optional[str] = None
    generated_at: str = ""
    title: str = "MedExplain AI - Clinical Decision Support Report"
    sections: List[ReportSection] = Field(default_factory=list)
    content: Dict[str, Any] = Field(
        default_factory=dict, description="Section key -> content, for direct frontend access"
    )
    summary: Dict[str, Any] = Field(default_factory=dict)
    safety_disclaimer: str = ""
    human_review_required: bool = True
    human_review_notice: str = ""
    autonomous_diagnosis: bool = False
    limitations: List[Limitations] = Field(default_factory=list)
    uncertainty: Uncertainty
    model: ModelInfo
    provenance: Provenance
    stages: List[StageTiming] = Field(default_factory=list)
    request_id: str = ""
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
