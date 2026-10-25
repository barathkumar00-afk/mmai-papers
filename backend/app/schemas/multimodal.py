from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.common import ModelInfo, Provenance, SafetyNotice, StageTiming, Uncertainty
from app.schemas.image import ImageAnalysisResponse
from app.schemas.speech import SpeechAnalysisResponse
from app.schemas.clinical import ClinicalAnalysisResponse

class PatientInfo(BaseModel):
    patient_id: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    medical_history: Optional[str] = None
    medications: Optional[str] = None
    comorbidities: Optional[str] = None

class ClinicalInput(BaseModel):
    spo2: str = Field(..., description="Oxygen saturation")
    crp: str = Field(..., description="C-Reactive Protein value")
    complaint: str = Field(..., description="Chief complaint")
    patient_info: Optional[PatientInfo] = None

class ObservedEvidence(BaseModel):
    evidence_id: str
    statement: str
    source: str
    modality: str
    confidence: Optional[float] = None
    detail: Optional[str] = None

class CandidateInterpretation(BaseModel):
    rank: int
    label: str
    probability: Optional[float] = None
    weight: Optional[float] = None
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    probability_is_calibrated: bool = False

class ModalityContribution(BaseModel):
    modality: str
    observations: List[str]
    evidence_count: int
    relative_support: Optional[float] = None
    method: str
    is_measured_attribution: bool = False

class MultimodalAnalysisResponse(BaseModel):
    success: bool = True
    case_id: str
    primary_finding: str
    rationale: str
    differential_ranking: List[CandidateInterpretation] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float
    uncertainty: float
    confidence_basis: str
    confidence_is_calibrated: bool = False
    observed_evidence: List[ObservedEvidence] = Field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    model_generated_interpretations: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    evidence_trace: List[str] = Field(default_factory=list)
    image: Optional[ImageAnalysisResponse] = None
    speech: Optional[SpeechAnalysisResponse] = None
    clinical: Optional[Any] = None
    unified_representation: Dict[str, Any] = Field(default_factory=dict)
    modality_contributions: List[ModalityContribution] = Field(default_factory=list)
    retrieval_query: str = ""
    uncertainty_block: Optional[Uncertainty] = None
    model: ModelInfo
    models: Dict[str, ModelInfo] = Field(default_factory=dict)
    limitations: List[Any] = Field(default_factory=list)
    safety: SafetyNotice
    provenance: Provenance
    stages: List[StageTiming] = Field(default_factory=list)
    latency_ms: float = 0.0
    request_id: str = ""
    warnings: List[str] = Field(default_factory=list)

class MultimodalAnalysisRequest(BaseModel):
    case_id: Optional[str] = None
    clinical_data: ClinicalInput
