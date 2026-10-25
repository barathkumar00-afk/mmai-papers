"""``POST /api/analyze/clinical`` -- structured clinical text normalization."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Form

from app.api.routes.deps import build_clinical_input
from app.core.logging import get_logger
from app.schemas.clinical import ClinicalAnalysisResponse, ClinicalInput
from app.services.clinical_service import clinical_service

router = APIRouter(tags=["Analysis"])
logger = get_logger(__name__)


@router.post(
    "/clinical",
    response_model=ClinicalAnalysisResponse,
    summary="Normalize clinical text into a structured patient representation",
)
async def analyze_clinical(
    symptoms: Optional[str] = Form(None, description="JSON array or ';' separated list"),
    history: Optional[str] = Form(None, description="JSON array or ';' separated list"),
    medications: Optional[str] = Form(None, description="JSON array or ';' separated list"),
    clinical_notes: Optional[str] = Form(None),
    chief_complaint: Optional[str] = Form(None),
    complaint: Optional[str] = Form(None, description="Workbench field: complaint / timeline"),
    vitals: Optional[str] = Form(None, description="JSON object, e.g. {\"spo2\": \"88%\"}"),
    labs: Optional[str] = Form(None, description="JSON object, e.g. {\"crp\": 42.4}"),
    spo2: Optional[str] = Form(None, description="Workbench field: SpO2, e.g. '88% (Ambient Air)'"),
    crp: Optional[str] = Form(None, description="Workbench field: CRP in mg/L"),
    comorbidities: Optional[str] = Form(None, description="Workbench field: comorbidity summary"),
    payload: Optional[ClinicalInput] = Body(None, include_in_body=False),
) -> ClinicalAnalysisResponse:
    if payload is not None and any(
        [
            payload.symptoms,
            payload.history,
            payload.medications,
            payload.clinical_notes,
            payload.chief_complaint,
            payload.complaint,
            payload.vitals,
            payload.labs,
            payload.spo2,
            payload.crp,
            payload.comorbidities,
        ]
    ):
        return await clinical_service.analyze(payload)

    clinical = await build_clinical_input(
        symptoms=symptoms,
        history=history,
        medications=medications,
        clinical_notes=clinical_notes,
        chief_complaint=chief_complaint,
        complaint=complaint,
        vitals=vitals,
        labs=labs,
        spo2=spo2,
        crp=crp,
        comorbidities=comorbidities,
    )
    return await clinical_service.analyze(clinical)
