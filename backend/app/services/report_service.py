"""Clinical decision-support report generation.

Produces a 14-section structured dossier. The report never claims autonomous
diagnosis, and every section is tagged with its provenance:

``observed``          measured or transcribed from the submitted artefacts
``retrieved``         returned by the local FAISS knowledge base
``model_generated``   produced by the configured local LLM
``none``              nothing available; the section says so
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.model_manager import model_manager
from app.schemas.common import Limitations, Provenance, SafetyNotice, Uncertainty
from app.schemas.multimodal import MultimodalAnalysisResponse
from app.schemas.report import ReportResponse, ReportSection
from app.services.explanation_service import explanation_service
from app.services.retrieval_service import retrieval_service
from app.utils.validation import clamp, dedupe_preserve_order, truncate

logger = get_logger(__name__)

NOT_AVAILABLE = "Not available for this request."


class ReportService:
    """Assembles the structured clinical decision-support report."""

    #: Canonical section order and titles.
    SECTION_SPEC: List[tuple[str, str]] = [
        ("case_summary", "Case Summary"),
        ("available_evidence", "Available Evidence"),
        ("image_observations", "Image Observations"),
        ("speech_findings", "Speech Findings"),
        ("clinical_data", "Clinical Data"),
        ("retrieved_evidence", "Retrieved Evidence"),
        ("candidate_interpretations", "Candidate Interpretations"),
        ("supporting_evidence", "Supporting Evidence"),
        ("contradicting_evidence", "Contradicting Evidence"),
        ("uncertainty", "Uncertainty"),
        ("missing_information", "Missing Information"),
        ("explainability_trail", "Explainability Trail"),
        ("human_review_requirement", "Human Review Requirement"),
        ("safety_disclaimer", "Safety Disclaimer"),
    ]

    def _limitations(self) -> List[Limitations]:
        return [
            Limitations(
                statement=(
                    "This report is AI-assisted decision support from a research prototype. It is "
                    "not a diagnosis, not a treatment plan, and not a substitute for clinical "
                    "judgement."
                ),
                category="clinical_safety",
            ),
            Limitations(
                statement=(
                    "The system has not been clinically validated. No accuracy, sensitivity, "
                    "specificity, F1, AUC, or hallucination-rate figure is claimed."
                ),
                category="validation_status",
            ),
            Limitations(
                statement=(
                    "Candidate weights are relative evidence-coverage shares, not diagnostic "
                    "probabilities."
                ),
                category="measurement_scope",
            ),
        ]

    # ------------------------------------------------------------------ build
    async def generate(
        self,
        *,
        analysis: Optional[MultimodalAnalysisResponse] = None,
        case_id: Optional[str] = None,
        query: str = "",
        top_k: int = 5,
        include_sections: Optional[Sequence[str]] = None,
        request_id: Optional[str] = None,
    ) -> ReportResponse:
        started = time.perf_counter()
        rid = request_id or uuid.uuid4().hex[:12]
        settings = get_settings()
        report_id = f"RPT-{uuid.uuid4().hex[:10].upper()}"
        warnings: List[str] = []

        if analysis is None:
            warnings.append(
                "No case analysis was supplied; this report is built from a text query only and "
                "contains no patient modality evidence."
            )
            search = await retrieval_service.search(query, top_k=top_k)
            retrieved_payload = search.get("evidence") or []
            if not search.get("knowledge_base_initialized"):
                warnings.append(search.get("message") or "Knowledge base not initialized")
            explanation = await explanation_service.explain(
                query=query, top_k=top_k, request_id=rid
            )
        else:
            retrieved_payload = analysis.retrieved_evidence
            explanation = await explanation_service.explain(analysis=analysis, request_id=rid)
            warnings.extend(analysis.warnings[:4])

        resolved_case_id = case_id or (analysis.case_id if analysis is not None else None)
        builders = {
            "case_summary": self._case_summary,
            "available_evidence": self._available_evidence,
            "image_observations": self._image_observations,
            "speech_findings": self._speech_findings,
            "clinical_data": self._clinical_data,
            "retrieved_evidence": self._retrieved_evidence,
            "candidate_interpretations": self._candidate_interpretations,
            "supporting_evidence": self._supporting_evidence,
            "contradicting_evidence": self._contradicting_evidence,
            "uncertainty": self._uncertainty,
            "missing_information": self._missing_information,
            "explainability_trail": self._explainability_trail,
            "human_review_requirement": self._human_review,
            "safety_disclaimer": self._safety_disclaimer,
        }

        wanted = {s.strip().lower() for s in (include_sections or []) if s.strip()}
        sections: List[ReportSection] = []
        for number, (key, title) in enumerate(self.SECTION_SPEC, start=1):
            if wanted and key not in wanted:
                continue
            content, populated, provenance, note = builders[key](
                analysis=analysis, explanation=explanation, retrieved=retrieved_payload
            )
            sections.append(
                ReportSection(
                    number=number,
                    key=key,
                    title=title,
                    content=content,
                    is_populated=populated,
                    provenance=provenance,
                    note=note,
                )
            )

        content_map: Dict[str, Any] = {section.key: section.content for section in sections}
        confidence = analysis.confidence if analysis is not None else 0.0
        uncertainty = Uncertainty(
            overall=round(clamp(1.0 - confidence), 4),
            confidence=confidence,
            drivers=(
                analysis.uncertainty_block.drivers
                if analysis is not None
                else ["No patient modality evidence was supplied."]
            )[:8],
            missing_information=(
                analysis.missing_information
                if analysis is not None
                else ["Complete patient modality evidence."]
            )[:10],
            notes=(
                analysis.confidence_basis if analysis is not None
                else "Confidence reflects retrieval availability only."
            ),
        )

        summary = {
            "case_id": resolved_case_id,
            "report_id": report_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "primary_finding": analysis.primary_finding if analysis is not None else NOT_AVAILABLE,
            "candidate_count": len(analysis.differential_ranking) if analysis is not None else 0,
            "observed_evidence_count": len(analysis.observed_evidence) if analysis is not None else 0,
            "retrieved_source_count": len(retrieved_payload),
            "confidence": confidence,
            "uncertainty": uncertainty.overall,
            "confidence_is_calibrated": False,
            "provenance": analysis.provenance.mode if analysis is not None else "real",
            "autonomous_diagnosis": False,
            "human_review_required": True,
        }

        return ReportResponse(
            success=True,
            report_id=report_id,
            case_id=resolved_case_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            sections=sections,
            content=content_map,
            summary=summary,
            safety_disclaimer=settings.SAFETY_DISCLAIMER,
            human_review_required=True,
            human_review_notice=settings.HUMAN_REVIEW_NOTICE,
            autonomous_diagnosis=False,
            limitations=self._limitations(),
            uncertainty=uncertainty,
            model=model_manager.fusion_info(),
            provenance=(
                analysis.provenance
                if analysis is not None
                else Provenance(
                    mode="real",
                    label="PARTIAL - RETRIEVAL ONLY",
                    computed_by="ReportService",
                    simulated=False,
                    notes="No patient modality evidence was supplied for this report.",
                )
            ),
            stages=list(analysis.stages) if analysis is not None else [],
            request_id=rid,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=dedupe_preserve_order(warnings)[:6],
        )

    # -------------------------------------------------------------- sections
    @staticmethod
    def _case_summary(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None:
            return NOT_AVAILABLE, False, "none", "No case analysis was supplied."
        parts = [
            f"Case: {analysis.case_id}",
            f"Modalities analysed: {', '.join(analysis.unified_representation.get('modalities_present', [])) or 'none'}",
            f"Observed evidence items: {len(analysis.observed_evidence)}",
            f"Retrieved sources: {len(analysis.retrieved_evidence)}",
            f"Candidate interpretations: {len(analysis.differential_ranking)}",
            f"Confidence: {analysis.confidence} (not a calibrated probability; basis: {analysis.confidence_basis})",
        ]
        return "\n".join(parts), True, "observed", ""

    @staticmethod
    def _available_evidence(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None:
            return NOT_AVAILABLE, False, "none", ""
        lines = [
            f"[{item.modality}/{item.source}] {item.statement}" for item in analysis.observed_evidence
        ]
        return (lines or ["No observed evidence was produced."]), bool(lines), "observed", ""

    @staticmethod
    def _image_observations(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None or analysis.image is None:
            return "No image was supplied for this report.", False, "none", ""
        image = analysis.image
        observations = [f"{o.source}: {o.finding}" for o in image.observations]
        features = [f"{f.name} = {f.value} ({f.category})" for f in image.visual_features]
        payload = {
            "modality": image.modality,
            "format": image.metadata.format,
            "dimensions": f"{image.metadata.width}x{image.metadata.height}",
            "is_dicom": image.metadata.is_dicom,
            "de_identified": image.metadata.de_identified,
            "observations": observations,
            "measured_features": features,
            "limitations": [item.statement for item in image.limitations],
            "provenance": image.provenance.label,
        }
        return payload, True, "observed" if not image.provenance.simulated else "model_generated", ""

    @staticmethod
    def _speech_findings(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None or analysis.speech is None:
            return "No audio was supplied for this report.", False, "none", ""
        speech = analysis.speech
        payload = {
            "transcript": speech.transcript or NOT_AVAILABLE,
            "observations": [
                f"[{o.source}] {o.observation}" for o in speech.clinical_observations
            ],
            "measured_features": [
                f"{f.name} = {f.value}{f.unit}" for f in speech.speech_features
            ],
            "duration_seconds": speech.metadata.duration_seconds,
            "provenance": speech.provenance.label,
        }
        return payload, bool(speech.transcript or speech.speech_features), "observed", ""

    @staticmethod
    def _clinical_data(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None or analysis.clinical is None:
            return "No clinical text was supplied for this report.", False, "none", ""
        clinical = analysis.clinical
        payload = {
            "symptoms": clinical.get("symptoms", []),
            "history": clinical.get("history", []),
            "labs": clinical.get("labs", {}),
            "vitals": clinical.get("vitals", {}),
            "medications": clinical.get("medications", []),
            "chief_complaint": clinical.get("chief_complaint", ""),
            "comorbidities": clinical.get("comorbidities", ""),
            "derived_features": [
                {"name": f["name"], "detail": f["detail"], "rule": f["rule"]}
                for f in clinical.get("clinical_features", [])
            ],
        }
        populated = bool(payload["symptoms"] or payload["labs"] or payload["vitals"] or payload["derived_features"])
        return payload, populated, "observed", ""

    @staticmethod
    def _retrieved_evidence(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if not retrieved:
            return "Knowledge base not initialized", False, "none", (
                "No FAISS index is available, so no external evidence could be cited. "
                "No citations are fabricated."
            )
        lines = [
            f"[doc:{item.get('document_id')}] {item.get('title') or 'untitled'} "
            f"(similarity {item.get('similarity')}, source {item.get('source')}): "
            f"{truncate(str(item.get('text') or ''), 500)}"
            for item in retrieved
        ]
        return lines, True, "retrieved", ""

    @staticmethod
    def _candidate_interpretations(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None or not analysis.differential_ranking:
            return (
                "No candidate interpretations were produced. This reflects insufficient "
                "grounded evidence, not a negative clinical result.",
                False,
                "none",
                "",
            )
        payload = [
            {
                "rank": c.rank,
                "label": c.label,
                "relative_support": c.weight,
                "is_calibrated_probability": False,
                "rationale": c.rationale,
                "supporting_count": len(c.supporting_evidence),
                "contradicting_count": len(c.contradicting_evidence),
            }
            for c in analysis.differential_ranking
        ]
        return payload, True, "model_generated", (
            "These are model-generated candidates for clinician review, not diagnoses. "
            "Weights are relative evidence-coverage shares."
        )

    @staticmethod
    def _supporting_evidence(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None or not analysis.differential_ranking:
            return NOT_AVAILABLE, False, "none", ""
        lines: List[str] = []
        for candidate in analysis.differential_ranking:
            for entry in candidate.supporting_evidence:
                lines.append(f"{candidate.label} <- {entry}")
        return (lines or ["No supporting evidence was verified for any candidate."]), bool(lines), "observed", ""

    @staticmethod
    def _contradicting_evidence(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None or not analysis.differential_ranking:
            return NOT_AVAILABLE, False, "none", ""
        lines: List[str] = []
        for candidate in analysis.differential_ranking:
            for entry in candidate.contradicting_evidence:
                lines.append(f"{candidate.label} <- {entry}")
        return (lines or ["No contradicting evidence was identified in the supplied evidence."]), bool(lines), "observed", ""

    @staticmethod
    def _uncertainty(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        if analysis is None:
            block = explanation.uncertainty
        else:
            block = analysis.uncertainty_block
        payload = {
            "overall": block.overall,
            "confidence": block.confidence,
            "epistemic": block.epistemic,
            "aleatoric": block.aleatoric,
            "is_calibrated": False,
            "drivers": block.drivers,
            "basis": block.notes,
        }
        return payload, True, "observed", "Confidence is a transparent heuristic, not a calibrated estimate."

    @staticmethod
    def _missing_information(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        items = (
            analysis.missing_information
            if analysis is not None
            else explanation.uncertainty.missing_information
        )
        return (items or ["None recorded."]), bool(items), "observed", ""

    @staticmethod
    def _explainability_trail(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        payload = {
            "attribution_method": explanation.attribution_method,
            "attribution_is_measured": explanation.attribution_is_measured,
            "attribution_disclaimer": explanation.attribution_disclaimer,
            "modality_contributions": {
                modality: {
                    "evidence_count": contribution.evidence_count,
                    "relative_support": contribution.relative_support,
                    "method": contribution.method,
                    "is_measured_attribution": contribution.is_measured_attribution,
                    "observations": contribution.observations,
                }
                for modality, contribution in explanation.modality_contributions.items()
            },
            "evidence_trail": [
                {
                    "step": step.step,
                    "stage": step.stage,
                    "label": step.label,
                    "detail": step.detail,
                    "source": step.source,
                    "method": step.method,
                }
                for step in explanation.evidence_trail
            ],
            "reasoning_steps": explanation.reasoning_steps,
        }
        return payload, bool(explanation.evidence_trail), "observed", explanation.attribution_disclaimer

    @staticmethod
    def _human_review(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        settings = get_settings()
        payload = [
            "This report requires review by a qualified healthcare professional.",
            settings.HUMAN_REVIEW_NOTICE,
            "No autonomous action may be taken on the basis of this output.",
            "Every candidate interpretation, weight, and observation must be independently verified.",
        ]
        return payload, True, "observed", ""

    @staticmethod
    def _safety_disclaimer(*, analysis, explanation, retrieved) -> tuple[Any, bool, str, str]:
        settings = get_settings()
        return [settings.SAFETY_DISCLAIMER], True, "observed", ""


report_service = ReportService()
