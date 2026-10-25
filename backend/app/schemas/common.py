"""Cross-cutting models shared by every schema module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

#: Applied to every non-clinical response so a consumer can always tell whether
#: values were computed or simulated.
PROVENANCE_REAL = "real"
PROVENANCE_SIMULATED = "simulated"


class Provenance(BaseModel):
    """Where a set of numbers came from.

    ``mode`` is ``"real"`` only when the values were actually computed by a
    configured local model or deterministic algorithm in this process.
    """

    mode: str = Field(PROVENANCE_SIMULATED, description="'real' or 'simulated'")
    label: str = Field("DEMO / SIMULATED", description="Human-readable provenance tag")
    computed_by: str = Field("", description="Model or algorithm that produced the values")
    simulated: bool = Field(True, description="True when values are demo placeholders")
    notes: str = Field("", description="Caveats about the values, if any")


class Uncertainty(BaseModel):
    """Explicit uncertainty block. Never silently omitted."""

    overall: float = Field(1.0, ge=0.0, le=1.0, description="Aggregate uncertainty in [0,1]")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="1 - overall uncertainty")
    epistemic: Optional[float] = Field(None, description="Reducible uncertainty (knowledge gaps)")
    aleatoric: Optional[float] = Field(None, description="Irreducible uncertainty (data noise)")
    drivers: List[str] = Field(default_factory=list, description="Reasons uncertainty is elevated")
    missing_information: List[str] = Field(default_factory=list, description="Absent data the model would need")
    notes: str = ""

    model_config = {"protected_namespaces": ()}


class EvidenceRef(BaseModel):
    """Pointer back to a specific region of a submitted artefact."""

    reference: str = Field(..., description="e.g. 'image:right_lower_zone'")
    label: str = ""
    region: Optional[Dict[str, float]] = Field(
        default=None,
        description="Normalized bounding box {x, y, width, height} in [0,1], or pixel coords",
    )
    coordinates: Optional[Dict[str, int]] = Field(
        default=None,
        description="Pixel-space point or box reference, when the model exposes one",
    )
    method: str = Field("", description="How the reference was derived")


class ModelInfo(BaseModel):
    """Identifies the model/configuration used, for reproducibility."""

    name: str = "unavailable"
    version: str = ""
    role: str = ""
    status: str = "unavailable"
    source: str = "local"
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"protected_namespaces": ()}


class Limitations(BaseModel):
    statement: str
    category: str = "general"


class MissingInformation(BaseModel):
    item: str
    reason: str = ""
    requested_from: str = "clinician"


class SafetyNotice(BaseModel):
    disclaimer: str
    human_review_required: bool = True
    human_review_notice: str
    not_autonomous_diagnosis: bool = True
    intended_use: str = "Clinical research prototype - decision support only"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class StageTiming(BaseModel):
    """Real wall-clock timings measured by the backend for each pipeline stage."""

    stage: str
    duration_ms: float
    simulated: bool = False
