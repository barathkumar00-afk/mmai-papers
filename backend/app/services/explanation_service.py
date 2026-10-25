"""Explainability service: builds an auditable evidence trail.

The trail is assembled from artefacts that genuinely exist in the request --
measured features, observed modality statements, real FAISS hits, and the
reasoning steps the RAG layer produced. Attribution values are *heuristic
evidence-coverage shares* and are labelled as such. No attention weight,
gradient saliency, or integrated-gradients value is ever reported, because no
model in this repository exposes one.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.model_manager import model_manager
from app.schemas.common import (
    Limitations,
    Provenance,
    SafetyNotice,
    Uncertainty,
)
from app.schemas.explanation import (
    EvidenceTrailStep,
    ExplanationResponse,
    ModalityContributionExplanation,
)
from app.schemas.multimodal import CandidateInterpretation, MultimodalAnalysisResponse, ObservedEvidence
from app.schemas.retrieval import RetrievedEvidence
from app.services.rag_service import rag_service
from app.services.retrieval_service import retrieval_service
from app.utils.validation import clamp, dedupe_preserve_order, truncate

logger = get_logger(__name__)

ATTRIBUTION_METHOD = "heuristic_evidence_coverage"
ATTRIBUTION_DISCLAIMER = (
    "Attribution is heuristic (based on evidence coverage and retrieval scores). "
    "It is not a measured attention weight or gradient-based explanation."
)


class ExplanationService:
    """Builds the evidence trail and per-modality contribution breakdown."""

    def _limitations(self) -> List[Limitations]:
        return [
            Limitations(
                statement=(
                    "Modality contributions are heuristic evidence-coverage shares. No model in "
                    "this system exposes attention weights or gradients, so none are reported."
                ),
                category="attribution_scope",
            ),
            Limitations(
                statement=(
                    "The trail records what the system did, not why a clinician should agree. "
                    "It supports verification; it does not replace it."
                ),
                category="explainability_scope",
            ),
        ]

    # ------------------------------------------------------------------ build
    def _trail(
        self,
        *,
        observed_by_modality: Dict[str, List[ObservedEvidence]],
        retrieved: Sequence[RetrievedEvidence],
        reasoning_steps: Sequence[str],
        candidates: Sequence[CandidateInterpretation],
        modalities: Sequence[str],
    ) -> List[EvidenceTrailStep]:
        steps: List[EvidenceTrailStep] = []
        counter = 0

        def add(**kwargs: Any) -> None:
            nonlocal counter
            counter += 1
            steps.append(EvidenceTrailStep(step=counter, **kwargs))

        # 1) raw evidence
        for modality in modalities:
            for item in observed_by_modality.get(modality, [])[:4]:
                add(
                    stage="raw_evidence",
                    label=f"{modality}:{item.evidence_id}",
                    detail=truncate(item.statement, 500),
                    source=item.source,
                    modality=modality,
                    method="direct observation from the submitted artefact",
                    supports=["feature"],
                )

        # 2) features -- measured / rule-derived evidence only
        for modality in modalities:
            feature_items = [
                item
                for item in observed_by_modality.get(modality, [])
                if item.source in {"measured", "rule_based"}
            ]
            for item in feature_items[:3]:
                add(
                    stage="feature",
                    label=f"{modality}:{item.evidence_id}",
                    detail=truncate(item.statement, 400),
                    source=item.source,
                    modality=modality,
                    method="deterministic measurement or rule evaluation",
                    supports=["modality_contribution"],
                )

        # 3) modality contribution
        contributions = self._contributions(observed_by_modality, candidates, modalities)
        for contribution in contributions:
            if contribution.evidence_count == 0:
                continue
            add(
                stage="modality_contribution",
                label=contribution.modality,
                detail=(
                    f"{contribution.evidence_count} evidence item(s) from {contribution.modality}; "
                    f"relative support {contribution.relative_support} by "
                    f"{contribution.method}."
                ),
                source="heuristic",
                modality=contribution.modality,
                method=contribution.method,
                is_measured_attribution=False,
                supports=["reasoning_step"],
                limitations=contribution.caveat,
            )

        # 4) retrieved evidence
        for item in retrieved:
            add(
                stage="retrieved_evidence",
                label=f"doc:{item.document_id}",
                detail=(
                    f"{item.title or 'untitled'} (chunk {item.chunk_index}); "
                    f"cosine similarity {item.similarity:.4f}."
                ),
                source="retrieved",
                method="FAISS cosine similarity over the local knowledge base",
                supports=["reasoning_step"],
            )

        # 5) reasoning steps
        for index, reasoning in enumerate(reasoning_steps, start=1):
            add(
                stage="reasoning_step",
                label=f"reasoning-{index}",
                detail=truncate(reasoning, 500),
                source="model_generated" if index > len(retrieved) else "pipeline",
                method="recorded pipeline action",
                supports=["candidate_interpretation"],
            )

        # 6) candidate interpretations
        for candidate in candidates:
            add(
                stage="candidate_interpretation",
                label=f"candidate-{candidate.rank}",
                detail=(
                    f"{candidate.label} | {len(candidate.supporting_evidence)} supporting, "
                    f"{len(candidate.contradicting_evidence)} contradicting evidence item(s)."
                ),
                source="model_generated",
                method="RAG reasoning over the supplied evidence only",
                supports=[],
                limitations="Not a diagnosis and not a calibrated probability.",
            )
        return steps

    def _contributions(
        self,
        observed_by_modality: Dict[str, List[ObservedEvidence]],
        candidates: Sequence[CandidateInterpretation],
        modalities: Sequence[str],
    ) -> List[ModalityContributionExplanation]:
        referenced = set()
        for candidate in candidates:
            for entry in candidate.supporting_evidence + candidate.contradicting_evidence:
                referenced.add(entry.split(":", 1)[0].strip())

        out: List[ModalityContributionExplanation] = []
        for modality in modalities:
            items = observed_by_modality.get(modality, [])
            cited = sum(1 for item in items if item.evidence_id in referenced)
            out.append(
                ModalityContributionExplanation(
                    modality=modality,
                    observations=[truncate(item.statement, 240) for item in items[:5]],
                    evidence_count=len(items),
                    relative_support=None,
                    method=ATTRIBUTION_METHOD,
                    is_measured_attribution=False,
                    caveat=ATTRIBUTION_DISCLAIMER,
                )
            )
        # Normalize only when at least one modality is actually cited.
        if any(sum(1 for i in observed_by_modality.get(m, []) if i.evidence_id in referenced) for m in modalities):
            raw = [
                sum(1 for item in observed_by_modality.get(m, []) if item.evidence_id in referenced)
                for m in modalities
            ]
            total = float(sum(raw)) or 1.0
            for contribution, value in zip(out, raw):
                contribution.relative_support = round(value / total, 4)
        else:
            total_items = sum(c.evidence_count for c in out) or 1
            for contribution in out:
                contribution.relative_support = round(contribution.evidence_count / total_items, 4)
        return out

    # ------------------------------------------------------------------ main
    async def explain(
        self,
        *,
        analysis: Optional[MultimodalAnalysisResponse] = None,
        query: str = "",
        top_k: int = 5,
        modalities: Optional[Sequence[str]] = None,
        request_id: Optional[str] = None,
    ) -> ExplanationResponse:
        started = time.perf_counter()
        rid = request_id or uuid.uuid4().hex[:12]
        settings = get_settings()
        selected = [m for m in (modalities or ["image", "speech", "clinical"])]

        warnings: List[str] = []
        observed_by_modality: Dict[str, List[ObservedEvidence]] = {"image": [], "speech": [], "clinical": []}
        candidates: List[CandidateInterpretation] = []
        reasoning_steps: List[str] = []
        retrieved: List[RetrievedEvidence] = []
        confidence = 0.0
        confidence_basis = "no analysis input was supplied"

        if analysis is not None:
            for item in analysis.observed_evidence:
                if item.modality in observed_by_modality:
                    observed_by_modality[item.modality].append(item)
            candidates = list(analysis.differential_ranking)
            reasoning_steps = list(analysis.evidence_trace)
            retrieved = [
                RetrievedEvidence(**{k: v for k, v in item.items() if k in RetrievedEvidence.model_fields})
                for item in analysis.retrieved_evidence
            ]
            confidence = analysis.confidence
            confidence_basis = analysis.confidence_basis
            warnings.extend(analysis.warnings[:5])
            if analysis.unified_representation.get("is_trained_neural_fusion_model") is False:
                warnings.append(
                    "The fusion layer is an integration component, not a trained multimodal "
                    "neural network; no cross-attention signals exist to attribute."
                )
        else:
            # Standalone mode: retrieve evidence for a free-text query only.
            if not query.strip():
                warnings.append(
                    "No case analysis was supplied and no query was provided, so the evidence "
                    "trail is empty."
                )
            search = await retrieval_service.search(query, top_k=top_k)
            retrieved = list(search.get("evidence") or [])
            if not search.get("knowledge_base_initialized"):
                warnings.append(search.get("message") or "Knowledge base not initialized")
            if retrieved:
                reasoning_steps = [
                    f"Retrieved {len(retrieved)} chunk(s) for the supplied query; no patient "
                    "modality evidence was available, so no candidate interpretation is produced."
                ]
            confidence_basis = (
                "No patient evidence was supplied; confidence reflects retrieval availability only."
            )

        trail = self._trail(
            observed_by_modality=observed_by_modality,
            retrieved=retrieved,
            reasoning_steps=reasoning_steps,
            candidates=candidates,
            modalities=selected,
        )
        contributions = self._contributions(observed_by_modality, candidates, selected)

        uncertainty = Uncertainty(
            overall=round(clamp(1.0 - confidence), 4),
            confidence=confidence,
            drivers=dedupe_preserve_order(
                (
                    [confidence_basis]
                    if confidence_basis
                    else []
                )
                + (["Attribution is heuristic, not a measured model signal."] if trail else [])
                + (["No knowledge base index is available."] if not retrieved else [])
            )[:8],
            missing_information=(
                list(analysis.missing_information) if analysis is not None else ["Patient modality evidence."]
            )[:10],
            notes=confidence_basis,
        )

        return ExplanationResponse(
            success=True,
            case_id=analysis.case_id if analysis is not None else None,
            evidence_trail=trail,
            modality_contributions={c.modality: c for c in contributions},
            modality_contribution_summary={
                c.modality: c.observations for c in contributions
            },
            retrieved_sources=[item.model_dump() for item in retrieved],
            reasoning_steps=list(reasoning_steps),
            candidate_interpretations=[c.model_dump() for c in candidates],
            attribution_method=ATTRIBUTION_METHOD,
            attribution_is_measured=False,
            attribution_disclaimer=ATTRIBUTION_DISCLAIMER,
            uncertainty=uncertainty,
            model=model_manager.fusion_info(),
            limitations=self._limitations(),
            safety=SafetyNotice(
                disclaimer=settings.SAFETY_DISCLAIMER,
                human_review_required=True,
                human_review_notice=settings.HUMAN_REVIEW_NOTICE,
            ),
            provenance=Provenance(
                mode="real",
                label="REAL PIPELINE TRACE",
                computed_by="ExplanationService",
                simulated=False,
                notes=(
                    "Every trail entry corresponds to an artefact that exists in this request. "
                    "Contribution values are heuristic shares, clearly labelled."
                ),
            ),
            request_id=rid,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=dedupe_preserve_order(warnings)[:6],
        )


explanation_service = ExplanationService()
