"""Schemas for the explainability endpoint."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import (
    EvidenceRef,
    Limitations,
    ModelInfo,
    Provenance,
    SafetyNotice,
    Uncertainty,
)


class EvidenceTrailStep(BaseModel):
    """One hop in the audit chain.

    ``method`` always states how the link was established. Attention or
    gradient attribution is only ever reported when a real model exposes it.
    """

    step: int
    stage: str = Field(
        ...,
        description="raw_evidence | feature | modality_contribution | retrieved_evidence | "
        "reasoning_step | candidate_interpretation",
    )
    label: str
    detail: str = ""
    source: str = "observed"
    modality: Optional[str] = None
    method: str = ""
    is_measured_attribution: bool = False
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    supports: List[str] = Field(default_factory=list, description="Downstream steps this feeds")
    limitations: str = ""


class ModalityContributionExplanation(BaseModel):
    """Per-modality contribution. Heuristic unless measured attribution exists."""

    modality: str
    observations: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    relative_support: Optional[float] = None
    method: str = "heuristic_evidence_coverage"
    is_measured_attribution: bool = False
    caveat: str = ""


class ExplanationRequest(BaseModel):
    """Re-uses a previously computed case by id, or accepts a fresh query."""

    case_id: Optional[str] = None
    query: str = ""
    top_k: int = 5
    modalities: List[str] = Field(
        default_factory=lambda: ["image", "speech", "clinical"],
        description="Subset of modalities to attribute",
    )


class ExplanationResponse(BaseModel):
    success: bool = True
    case_id: Optional[str] = None
    evidence_trail: List[EvidenceTrailStep] = Field(default_factory=list)
    modality_contributions: Dict[str, ModalityContributionExplanation] = Field(
        default_factory=dict
    )
    #: Flat convenience shape, one entry per modality.
    modality_contribution_summary: Dict[str, List[str]] = Field(default_factory=dict)
    retrieved_sources: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)
    candidate_interpretations: List[Dict[str, Any]] = Field(default_factory=list)
    attribution_method: str = "heuristic_evidence_coverage"
    attribution_is_measured: bool = Field(
        False,
        description="False unless a real model exposed attention/gradient signals",
    )
    attribution_disclaimer: str = (
        "Attribution is heuristic (based on evidence coverage and retrieval scores). "
        "It is not a measured attention weight or gradient-based explanation."
    )
    uncertainty: Uncertainty
    model: ModelInfo
    limitations: List[Limitations] = Field(default_factory=list)
    safety: SafetyNotice
    provenance: Provenance
    request_id: str = ""
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
