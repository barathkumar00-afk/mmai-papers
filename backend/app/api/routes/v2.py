"""``/api/v2/*`` -- compatibility layer matching the contracts the existing
frontend already documents in ``ApiEthicsSection.tsx``.

Why this exists
---------------
The frontend publishes six ``/api/v2/*`` request/response examples. Rather than
forcing the frontend to adopt new endpoint names, those exact contracts are
implemented here on top of the same real services used by ``/api/*``.

Honesty policy
--------------
Several documented response fields (``patch_tokens``, ``saliency_coordinates``,
``cross_attention_entropy``, ``latent_representation``, ``dyspnea_index``,
``burst_rate_bpm``, ``tabular_prior``, ``hypoxemia_risk``, ``dossier_pdf_url``)
imply trained models and attention signals that **do not exist in this
repository**. This module therefore never fabricates them. Each such field is
returned as ``null`` with a paired ``*_status`` value, and every response
carries an ``unsupported_fields`` list plus provenance metadata explaining what
is real and what is absent.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.clinical import ClinicalInput
from app.services.case_store import case_store
from app.services.clinical_service import clinical_service
from app.services.fusion_service import multimodal_fusion_service
from app.services.retrieval_service import retrieval_service
from app.services.speech_service import speech_service
from app.services.vision_service import vision_service
from app.utils.image_utils import decode_base64_image
from app.utils.validation import clamp

router = APIRouter(tags=["v2 Compatibility"])
logger = get_logger(__name__)

NO_TRAINED_MODEL = "not_available_no_trained_model_in_repository"


# --------------------------------------------------------------------- schemas
class V2ImageRequest(BaseModel):
    dicom_b64: Optional[str] = None
    image_b64: Optional[str] = None
    window_level: Optional[List[float]] = Field(None, description="[center, width]")
    de_identify: bool = True
    modality_hint: Optional[str] = None


class V2SpeechRequest(BaseModel):
    audio_clip_wav: Optional[str] = None
    audio_b64: Optional[str] = None
    sample_rate_hz: Optional[int] = None
    language: Optional[str] = None


class V2ClinicalRequest(BaseModel):
    patient_id: Optional[str] = None
    fhir_bundle_json: Optional[Dict[str, Any]] = None
    complaint: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    vitals: Dict[str, Any] = Field(default_factory=dict)
    labs: Dict[str, Any] = Field(default_factory=dict)


class V2MultimodalRequest(BaseModel):
    case_id: str = "#MED-2025-0941"
    image_dicom_b64: Optional[str] = None
    audio_clip_wav: Optional[str] = None
    complaint: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    vitals: Dict[str, Any] = Field(default_factory=dict)
    labs: Dict[str, Any] = Field(default_factory=dict)
    weights: Dict[str, float] = Field(default_factory=dict)
    top_k: int = 5


class V2RetrieveRequest(BaseModel):
    latent_query: Optional[List[float]] = None
    query: Optional[str] = None
    top_k: int = 3
    societies: List[str] = Field(default_factory=list)


class V2ReportRequest(BaseModel):
    case_id: str = "#MED-2025-0941"
    attending_signature_token: Optional[str] = None


# ---------------------------------------------------------------------- utils
def _first_b64(*values: Optional[str]) -> Optional[bytes]:
    for value in values:
        if value and value.strip():
            return decode_base64_image(value)
    return None


def _unsupported(names: List[str], reason: str = NO_TRAINED_MODEL) -> Dict[str, Any]:
    return {
        "unsupported_fields": names,
        "unsupported_reason": reason,
        "no_fabrication_policy": (
            "Fields requiring a trained or attention-exposing model are returned as null "
            "rather than being invented."
        ),
    }


def _envelope(service: str, **payload: Any) -> Dict[str, Any]:
    settings = get_settings()
    body: Dict[str, Any] = {
        "success": True,
        "service": service,
        "mock_mode": settings.MOCK_MODE,
        "human_review_required": True,
        "notice": settings.HUMAN_REVIEW_NOTICE,
        "autonomous_diagnosis": False,
        "request_id": uuid.uuid4().hex[:12],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    body.update(payload)
    return body


# ---------------------------------------------------------------------- routes
@router.post("/analyze/image", summary="v2: image analysis (DICOM base64)")
async def v2_analyze_image(request: V2ImageRequest) -> Dict[str, Any]:
    data = _first_b64(request.dicom_b64, request.image_b64)
    if not data:
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "Send 'dicom_b64' (or 'image_b64') containing a base64-encoded image.",
            status_code=400,
        )
    result = await vision_service.analyze(
        data,
        filename="upload.dcm",
        modality_hint=request.modality_hint,
        window_level=request.window_level,
        de_identify=request.de_identify,
    )
    return _envelope(
        "image",
        **_unsupported(
            [
                "patch_tokens: requires a trained vision encoder exposing patch token grids",
                "saliency_coordinates: requires gradient/attention attribution from a trained VLM",
            ]
        ),
        patch_tokens=None,
        patch_tokens_status=NO_TRAINED_MODEL,
        saliency_coordinates=None,
        saliency_coordinates_status=NO_TRAINED_MODEL,
        latency_ms=result.latency_ms,
        # Real, computed values.
        modality=result.modality,
        measured_visual_features=[
            {"name": f.name, "value": f.value, "category": f.category, "measured": f.measured}
            for f in result.visual_features
        ],
        observations=[
            {"finding": o.finding, "source": o.source, "confidence": o.confidence}
            for o in result.observations
        ],
        evidence_regions=[ref.model_dump() for ref in result.evidence_regions],
        uncertainty=result.uncertainty.model_dump(),
        provenance=result.provenance.model_dump(),
    )


@router.post("/analyze/speech", summary="v2: speech analysis (WAV base64)")
async def v2_analyze_speech(request: V2SpeechRequest) -> Dict[str, Any]:
    data = _first_b64(request.audio_clip_wav, request.audio_b64)
    if not data:
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "Send 'audio_clip_wav' containing a base64-encoded audio clip.",
            status_code=400,
        )
    result = await speech_service.analyze(
        data, filename="clip.wav", language=request.language
    )
    return _envelope(
        "speech",
        **_unsupported(
            [
                "dyspnea_index: requires a clinically validated dyspnea classifier; "
                "a rule-based index is not clinically validated and is therefore not reported",
                "burst_rate_bpm: requires a validated respiratory acoustic model",
                "stridor_detected: requires a validated airway-sound classifier",
            ]
        ),
        dyspnea_index=None,
        dyspnea_index_status=NO_TRAINED_MODEL,
        burst_rate_bpm=None,
        burst_rate_bpm_status=NO_TRAINED_MODEL,
        stridor_detected=None,
        stridor_detected_status=NO_TRAINED_MODEL,
        latency_ms=result.latency_ms,
        # Real, computed values.
        transcript=result.transcript,
        clinical_observations=[o.model_dump() for o in result.clinical_observations],
        measured_acoustic_features=[
            {"name": f.name, "value": f.value, "unit": f.unit, "measured": f.measured, "notes": f.notes}
            for f in result.speech_features
        ],
        audio_metadata=result.metadata.model_dump(),
        uncertainty=result.uncertainty.model_dump(),
        provenance=result.provenance.model_dump(),
    )


@router.post("/analyze/clinical", summary="v2: clinical data normalization (FHIR bundle)")
async def v2_analyze_clinical(request: V2ClinicalRequest) -> Dict[str, Any]:
    symptoms = list(request.symptoms)
    vitals = dict(request.vitals)
    labs = dict(request.labs)
    notes = ""

    if request.fhir_bundle_json:
        symptoms, vitals, labs, notes = _flatten_fhir(request.fhir_bundle_json, symptoms, vitals, labs)

    payload = ClinicalInput(
        symptoms=symptoms,
        vitals=vitals,
        labs=labs,
        clinical_notes=notes,
        complaint=request.complaint or "",
    )
    if not any([symptoms, vitals, labs, notes, request.complaint]):
        raise AppError(
            ErrorCode.MALFORMED_CLINICAL_DATA,
            "Send 'fhir_bundle_json', or 'symptoms' / 'vitals' / 'labs' / 'complaint'.",
            status_code=400,
        )

    result = await clinical_service.analyze(payload)
    crp = labs.get("crp")
    try:
        normalized_crp = float(crp) if crp is not None else None
    except (TypeError, ValueError):
        normalized_crp = None

    hypoxemic = any(f.name == "hypoxemia" for f in result.clinical_features)
    return _envelope(
        "clinical",
        **_unsupported(
            [
                "tabular_prior: requires a trained tabular/EHR prior network",
                "hypoxemia_risk: requires a calibrated, clinically validated risk model",
            ]
        ),
        tabular_prior=None,
        tabular_prior_status=NO_TRAINED_MODEL,
        hypoxemia_risk=None,
        hypoxemia_risk_status=NO_TRAINED_MODEL,
        # Real, computed values.
        patient_id=request.patient_id,
        normalized_crp=normalized_crp,
        hypoxemia_flag_observed=hypoxemic,
        hypoxemia_flag_basis=(
            "Deterministic threshold check: SpO2 < 92%. This is a flag for review, not a "
            "calibrated risk score."
        ),
        latency_ms=result.latency_ms,
        structured_patient_representation=result.patient_representation,
        clinical_features=[f.model_dump() for f in result.clinical_features],
        uncertainty=result.uncertainty.model_dump(),
        provenance=result.provenance.model_dump(),
    )


@router.post("/analyze/multimodal", summary="v2: multimodal orchestration")
async def v2_analyze_multimodal(request: V2MultimodalRequest) -> Dict[str, Any]:
    image_data = _first_b64(request.image_dicom_b64)
    audio_data = _first_b64(request.audio_clip_wav)
    clinical = ClinicalInput(
        symptoms=request.symptoms,
        vitals=request.vitals,
        labs=request.labs,
        complaint=request.complaint or "",
    )
    if not image_data and not audio_data and not clinical.all_text().strip():
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            "Provide at least one of: image_dicom_b64, audio_clip_wav, or clinical fields.",
            status_code=400,
        )

    result = await multimodal_fusion_service.analyze(
        image_data=image_data,
        audio_data=audio_data,
        clinical=clinical if clinical.all_text().strip() else None,
        case_id=request.case_id,
        top_k=max(1, min(request.top_k, 25)),
        weights=request.weights,
    )
    case_store.put(request.case_id, result)

    return _envelope(
        "multimodal",
        **_unsupported(
            [
                "latent_representation: the fusion layer is an integration service, not a trained "
                "joint-embedding model, so no [1, 2048] latent vector exists",
                "cross_attention_entropy: requires a cross-attention mechanism that this system "
                "does not contain",
            ]
        ),
        latent_representation=None,
        latent_representation_status="integration_layer_no_joint_embedding_space",
        cross_attention_entropy=None,
        cross_attention_entropy_status="integration_layer_no_cross_attention",
        latency_ms=result.latency_ms,
        # Real, computed values.
        case_id=result.case_id,
        confidence=result.confidence,
        confidence_is_calibrated=False,
        confidence_basis=result.confidence_basis,
        uncertainty=result.uncertainty,
        primary_finding=result.primary_finding,
        candidate_interpretations=[c.model_dump() for c in result.differential_ranking],
        observed_evidence=[e.model_dump() for e in result.observed_evidence],
        retrieved_evidence=result.retrieved_evidence,
        modality_contributions=[c.model_dump() for c in result.modality_contributions],
        attribution_method="heuristic_evidence_coverage",
        attribution_is_measured=False,
        unified_representation=result.unified_representation,
        safety=result.safety.model_dump(),
        provenance=result.provenance.model_dump(),
        stages=[s.model_dump() for s in result.stages],
    )


@router.post("/retrieve/evidence", summary="v2: evidence retrieval")
async def v2_retrieve_evidence(request: V2RetrieveRequest) -> Dict[str, Any]:
    result = await retrieval_service.search(
        request.query or "",
        top_k=max(1, min(request.top_k, 25)),
        latent_query=request.latent_query,
        societies=request.societies,
    )
    evidence = result.get("evidence") or []

    citations: List[Dict[str, Any]] = []
    for item in evidence:
        citations.append(
            {
                "pmid": int(item.pmid) if item.pmid and str(item.pmid).isdigit() else item.pmid,
                "guideline": item.title or item.chunk_id,
                "society": item.society,
                "relevance": round(max(item.similarity, 0.0), 6),
                "relevance_basis": "faiss_cosine_similarity (retrieval score, not clinical relevance)",
                "document_id": item.document_id,
                "source": item.source,
                "quote": item.text,
                "is_fabricated": False,
            }
        )

    if not evidence:
        message = result.get("message") or "Knowledge base not initialized"
    else:
        message = None

    return _envelope(
        "retrieval",
        citations=citations,
        index_status=result.get("index_status", "uninitialized"),
        knowledge_base_initialized=bool(result.get("knowledge_base_initialized")),
        message=message,
        no_citation_fabrication=(
            "Citations are only ever returned from the local FAISS index. When the index is "
            "empty the response contains no citations."
        ),
    )


@router.post("/generate/report", summary="v2: clinical dossier reference")
async def v2_generate_report(request: V2ReportRequest) -> Dict[str, Any]:
    from app.services.report_service import report_service

    analysis = case_store.get(request.case_id)
    if analysis is None:
        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            f"No cached analysis for case '{request.case_id}'. Run POST /api/v2/analyze/multimodal "
            "for this case first.",
            status_code=404,
        )

    report = await report_service.generate(analysis=analysis, case_id=request.case_id)
    # A deterministic content digest of the actual report payload. This is a real
    # hash of what was produced -- not a signature and not a stored artefact URL.
    digest_input = report.model_dump_json(exclude={"request_id", "latency_ms", "stages"}).encode("utf-8")
    sha256 = hashlib.sha256(digest_input).hexdigest()

    return _envelope(
        "report",
        **_unsupported(
            [
                "dossier_pdf_url: no PDF renderer or object store is configured; the report is "
                "returned as JSON only",
                "attending_signature_token / cryptographic attestation: no signing service is "
                "configured and no signature is fabricated",
            ]
        ),
        dossier_pdf_url=None,
        dossier_pdf_url_status="no_pdf_renderer_configured",
        signature_status="not_signed_no_signing_service_configured",
        signature_token_provided=bool(request.attending_signature_token),
        report_id=report.report_id,
        generated_at=report.generated_at,
        sha256=sha256,
        sha256_basis="sha256 of this response's report payload; not a signed attestation",
        human_review_required=True,
        autonomous_diagnosis=False,
        summary=report.summary,
        sections=[section.model_dump() for section in report.sections],
        safety_disclaimer=report.safety_disclaimer,
        human_review_notice=report.human_review_notice,
        provenance=report.provenance.model_dump(),
    )


# --------------------------------------------------------------------- helpers
def _flatten_fhir(
    bundle: Dict[str, Any],
    symptoms: List[str],
    vitals: Dict[str, Any],
    labs: Dict[str, Any],
) -> tuple[List[str], Dict[str, Any], Dict[str, Any], str]:
    """Extract a minimal, non-diagnostic view from a FHIR bundle.

    Deliberately shallow: observations, vitals and conditions are read for
    *reported* values only. No code system is interpreted and no diagnosis is
    derived from a coded value.
    """
    notes: List[str] = []
    entries = bundle.get("entry")
    if not isinstance(entries, list):
        return symptoms, vitals, labs, ""

    loinc_map = {
        "2708-6": "spo2",
        "59408-5": "spo2",
        "1988-5": "crp",
        "2160-0": "creatinine",
        "6690-2": "leukocytes",
        "718-7": "hb",
        "777-3": "platelets",
        "33762-6": "pao2",
        "2009-6": "tropponin",
        "3094-0": "bun",
    }

    for entry in entries:
        resource = (entry or {}).get("resource", {}) if isinstance(entry, dict) else {}
        if not isinstance(resource, dict):
            continue
        kind = resource.get("resourceType")

        if kind == "Observation":
            name = _fhir_name(resource)
            key = loinc_map.get(_fhir_code(resource), name)
            value = _fhir_value(resource)
            if key and value is not None:
                if key in {"spo2", "pao2", "heart_rate", "respiratory_rate", "temperature"}:
                    vitals[key] = value
                else:
                    labs[key] = value

        elif kind == "Condition":
            name = _fhir_name(resource)
            if name:
                symptoms.append(name)

        elif kind == "MedicationRequest":
            name = _fhir_name(resource)
            if name:
                notes.append(f"Medication requested: {name}")

        elif kind in {"DocumentReference", "Composition"}:
            text = _fhir_text(resource)
            if text:
                notes.append(text[:2000])

    return symptoms, vitals, labs, "\n".join(notes)


def _fhir_name(resource: Dict[str, Any]) -> str:
    coding = (((resource.get("code") or {}).get("coding")) or [])
    for entry in coding:
        display = entry.get("display") if isinstance(entry, dict) else None
        if display:
            return str(display).lower().replace(" ", "_")[:60]
    text = ((resource.get("code") or {}).get("text"))
    if text:
        return str(text).lower().replace(" ", "_")[:60]
    text = resource.get("text")
    return str(text)[:60] if isinstance(text, str) else ""


def _fhir_code(resource: Dict[str, Any]) -> str:
    coding = (((resource.get("code") or {}).get("coding")) or [])
    for entry in coding:
        if isinstance(entry, dict) and entry.get("code"):
            return str(entry["code"])
    return ""


def _fhir_value(resource: Dict[str, Any]) -> Any:
    value = resource.get("valueQuantity")
    if isinstance(value, dict) and value.get("value") is not None:
        return value["value"]
    if resource.get("valueString") is not None:
        return str(resource["valueString"])
    if resource.get("valueBoolean") is not None:
        return resource["valueBoolean"]
    return None


def _fhir_text(resource: Dict[str, Any]) -> str:
    text = resource.get("text") or (resource.get("content") or {}).get("text")
    return str(text) if isinstance(text, str) else ""
