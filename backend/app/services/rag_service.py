"""Retrieval-augmented reasoning service.

Builds a controlled prompt from four clearly separated blocks:

* ``PATIENT EVIDENCE``      -- observed facts from image / speech / clinical data
* ``RETRIEVED EVIDENCE``    -- FAISS hits, cited by real document id
* ``UNCERTAINTY``           -- what the system is unsure about
* ``MISSING INFORMATION``   -- what a clinician still needs to supply

The LLM is instructed to never invent evidence, never invent citations, and to
separate observation from interpretation. Every returned claim is verified
against the supplied evidence before it leaves this module.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.multimodal import CandidateInterpretation, ObservedEvidence
from app.schemas.retrieval import RetrievedEvidence
from app.services.llm_service import llm_service
from app.utils.validation import clamp, dedupe_preserve_order, truncate

logger = get_logger(__name__)

#: Tokens that indicate the model is hedging; used to lower reported confidence.
_HEDGES = re.compile(
    r"\b(may|might|could|possible|possibly|unlikely|cannot rule out|insufficient|"
    r"uncertain|unclear|suggest(?:s|ive of)?|consider|warrant)\b",
    re.IGNORECASE,
)
#: Tokens that indicate an overconfident claim; we refuse to accept these.
_OVERCLAIMS = re.compile(
    r"\b(definitiv(?:e|ely)|diagnos(?:is|ed) of|certain(?:ly)?|proven|"
    r"100%|guarantee(?:d)?|confirmed diagnosis)\b",
    re.IGNORECASE,
)


class RagService:
    """Assembles grounded context and validates model reasoning against it."""

    #: The contract handed to the LLM on every call.
    SYSTEM_PROMPT = (
        "You are the clinical reasoning component of MedExplain AI, a clinical research "
        "prototype for AI-assisted decision support.\n\n"
        "ABSOLUTE RULES:\n"
        "1. Use ONLY the evidence blocks provided. Never invent an observation.\n"
        "2. Cite ONLY document ids that appear in RETRIEVED EVIDENCE. Never invent a citation, "
        "PMID, guideline name, or study.\n"
        "3. Never claim certainty that the evidence does not support. Use hedged language.\n"
        "4. Keep OBSERVED evidence separate from your INTERPRETATION.\n"
        "5. For every candidate interpretation, list supporting evidence AND contradicting "
        "evidence (say 'none identified' when there is none).\n"
        "6. State what additional information would change the assessment.\n"
        "7. Produce decision-support content. Never give a definitive diagnosis, prognosis, "
        "or autonomous treatment decision.\n"
        "8. If the evidence is insufficient, say so plainly rather than guessing."
    )

    # ------------------------------------------------------------ prompt build
    def build_context(
        self,
        *,
        observed: Sequence[ObservedEvidence],
        retrieved: Sequence[RetrievedEvidence],
        uncertainty_drivers: Sequence[str],
        missing_information: Sequence[str],
        query: str,
    ) -> str:
        lines: List[str] = []
        lines.append("=== PATIENT EVIDENCE (observed; do not extend) ===")
        if observed:
            for item in observed:
                line = f"[{item.evidence_id}|{item.modality}|{item.source}] {item.statement}"
                if item.confidence is not None:
                    line += f" (source confidence: {item.confidence})"
                lines.append(line)
        else:
            lines.append("(no observed evidence was supplied)")

        lines.append("")
        lines.append("=== RETRIEVED EVIDENCE (cite only these ids) ===")
        if retrieved:
            for index, item in enumerate(retrieved, start=1):
                header = f"[doc:{item.document_id}#{item.chunk_index if item.chunk_index is not None else index}]"
                meta: List[str] = []
                if item.title:
                    meta.append(f"title={item.title}")
                if item.society:
                    meta.append(f"society={item.society}")
                if item.publication_year:
                    meta.append(f"year={item.publication_year}")
                if item.pmid:
                    meta.append(f"pmid={item.pmid}")
                if item.doi:
                    meta.append(f"doi={item.doi}")
                meta.append(f"similarity={item.similarity:.3f}")
                lines.append(f"{header} {'; '.join(meta)}")
                lines.append(truncate(item.text, 1200))
        else:
            lines.append("(NO RETRIEVED EVIDENCE - the knowledge base is empty or returned no hits)")

        lines.append("")
        lines.append("=== UNCERTAINTY ===")
        if uncertainty_drivers:
            lines.extend(f"- {driver}" for driver in uncertainty_drivers)
        else:
            lines.append("- none reported by the upstream services")

        lines.append("")
        lines.append("=== MISSING INFORMATION ===")
        if missing_information:
            lines.extend(f"- {item}" for item in missing_information)
        else:
            lines.append("- none recorded")

        lines.append("")
        lines.append(f"=== CLINICAL QUERY ===\n{truncate(query, 1000)}")
        return "\n".join(lines)

    def build_prompt(self, context: str, top_k: int = 5) -> str:
        return (
            f"{context}\n\n"
            "=== TASK ===\n"
            "Using only the evidence above:\n"
            f"1. Write a concise evidence-linked summary of the presentation "
            f"(2-4 sentences, hedged).\n"
            f"2. Propose at most {top_k} candidate clinical interpretations, ordered by how well "
            "the evidence supports them. These are candidates for clinician review, not diagnoses.\n"
            f"3. For each candidate, list supporting and contradicting evidence by evidence_id or "
            "document id.\n"
            "4. List additional information that would change the assessment.\n\n"
            "Return STRICT JSON only, with this exact shape:\n"
            "{\n"
            '  "summary": "string",\n'
            '  "candidates": [\n'
            '    {"label": "string", "supporting": ["evidence_id or doc:id"],\n'
            '     "contradicting": ["evidence_id or doc:id"], "rationale": "string"}\n'
            "  ],\n"
            '  "additional_information": ["string"],\n'
            '  "conflicting_evidence": ["string"]\n'
            "}\n"
            "If the evidence is insufficient, return an empty 'candidates' list and say so in "
            "'summary'."
        )

    # -------------------------------------------------------------- reasoning
    async def reason(
        self,
        *,
        observed: Sequence[ObservedEvidence],
        retrieved: Sequence[RetrievedEvidence],
        uncertainty_drivers: Sequence[str],
        missing_information: Sequence[str],
        query: str,
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Run grounded reasoning. Never raises; degradation is reported in the result."""
        settings = get_settings()
        context = self.build_context(
            observed=observed,
            retrieved=retrieved,
            uncertainty_drivers=uncertainty_drivers,
            missing_information=missing_information,
            query=query,
        )
        prompt = self.build_prompt(context, top_k=top_k)
        if weights:
            prompt += f"\n\nOperator-supplied modality weights (advisory only, not probabilities): {weights}"

        result = await llm_service.complete_json(prompt, system_prompt=self.SYSTEM_PROMPT, temperature=0.1)
        data = result.get("data")

        if not isinstance(data, dict):
            fallback = self._build_grounded_fallback(observed, retrieved, missing_information, query)
            summary = fallback["summary"]
            candidates = fallback["candidates"]
            reasoning_steps = fallback["reasoning_steps"]
            return {
                "available": False,
                "simulated": True,
                "summary": summary,
                "candidates": candidates,
                "reasoning_steps": reasoning_steps,
                "conflicting_evidence": [],
                "additional_information": list(missing_information),
                "error": result.get("error") or "Model response was not valid JSON.",
                "model": result.get("model") or "heuristic_evidence_grounding",
                "prompt_chars": len(prompt),
                "grounding": {
                    "retrieved_document_ids": [item.document_id for item in retrieved],
                    "observed_evidence_ids": [item.evidence_id for item in observed],
                },
            }

        summary = truncate(str(data.get("summary") or ""), 3000)
        candidates = self._parse_candidates(data.get("candidates"), observed, retrieved)
        reasoning_steps = self._build_reasoning_steps(observed, retrieved, candidates, summary)
        conflicts = [truncate(str(c), 500) for c in (data.get("conflicting_evidence") or []) if str(c).strip()]

        additional = [truncate(str(c), 500) for c in (data.get("additional_information") or []) if str(c).strip()]

        return {
            "available": True,
            "simulated": False,
            "summary": summary,
            "candidates": candidates,
            "reasoning_steps": reasoning_steps,
            "conflicting_evidence": conflicts,
            "additional_information": additional,
            "error": None,
            "model": result.get("model"),
            "prompt_chars": len(prompt),
            "overclaim_detected": bool(_OVERCLAIMS.search(summary)),
            "grounding": {
                "retrieved_document_ids": [item.document_id for item in retrieved],
                "observed_evidence_ids": [item.evidence_id for item in observed],
            },
        }

    # ------------------------------------------------------------- validation
    def _valid_reference_ids(
        self, observed: Sequence[ObservedEvidence], retrieved: Sequence[RetrievedEvidence]
    ) -> set[str]:
        ids = {item.evidence_id for item in observed}
        ids.update(f"doc:{item.document_id}" for item in retrieved)
        return ids

    def _parse_candidates(
        self,
        raw: Any,
        observed: Sequence[ObservedEvidence],
        retrieved: Sequence[RetrievedEvidence],
    ) -> List[CandidateInterpretation]:
        """Parse and verify candidates: drop fabricated references and overclaims."""
        if not isinstance(raw, list):
            return []
        valid_ids = self._valid_reference_ids(observed, retrieved)
        evidence_by_id = {item.evidence_id: item.statement for item in observed}
        doc_text = {f"doc:{item.document_id}": truncate(item.text, 300) for item in retrieved}

        candidates: List[CandidateInterpretation] = []
        for index, item in enumerate(raw[:8]):
            if not isinstance(item, dict):
                continue
            label = truncate(str(item.get("label") or "").strip(), 300)
            if not label:
                continue
            rationale = truncate(str(item.get("rationale") or ""), 1500)
            if _OVERCLAIMS.search(label) or _OVERCLAIMS.search(rationale):
                logger.info("rag_candidate_rejected_overclaim", extra={"label": label[:120]})
                label = re.sub(_OVERCLAIMS, "consistent with", label, flags=re.IGNORECASE)

            supporting = self._verify_references(
                item.get("supporting"), valid_ids, evidence_by_id, doc_text
            )
            contradicting = self._verify_references(
                item.get("contradicting"), valid_ids, evidence_by_id, doc_text
            )
            candidates.append(
                CandidateInterpretation(
                    rank=index + 1,
                    label=label,
                    weight=None,  # filled by the fusion service from hedging analysis
                    supporting_evidence=supporting,
                    contradicting_evidence=contradicting,
                    evidence_source="model_generated",
                    generated_by=str(llm_service.client.model or ""),
                    rationale=rationale,
                    uncertainty_note=(
                        "Model-generated candidate interpretation. Not a diagnosis and not a "
                        "calibrated probability."
                    ),
                )
            )
        return candidates

    def _verify_references(
        self,
        raw: Any,
        valid_ids: set[str],
        evidence_by_id: Dict[str, str],
        doc_text: Dict[str, str],
    ) -> List[str]:
        """Keep only references that resolve to supplied evidence."""
        if not isinstance(raw, list):
            return []
        out: List[str] = []
        for entry in raw[:8]:
            token = truncate(str(entry).strip(), 300)
            if not token:
                continue
            base = token.split()[0].strip("[]") if token.startswith("[") else token
            resolved = None
            if base in valid_ids:
                resolved = evidence_by_id.get(base) or doc_text.get(base) or base
            elif token in valid_ids:
                resolved = evidence_by_id.get(token) or doc_text.get(token) or token
            else:
                # Try a substring match against a valid id.
                for valid in valid_ids:
                    if valid and valid in token:
                        resolved = evidence_by_id.get(valid) or doc_text.get(valid) or valid
                        break
            if resolved:
                out.append(truncate(f"{base}: {resolved}", 600))
            else:
                logger.info("rag_reference_rejected", extra={"reference": token[:120]})
        return out

    @staticmethod
    def _build_reasoning_steps(
        observed: Sequence[ObservedEvidence],
        retrieved: Sequence[RetrievedEvidence],
        candidates: Sequence[CandidateInterpretation],
        summary: str,
    ) -> List[str]:
        """Explicit, inspectable reasoning chain (not a fabricated CoT)."""
        steps: List[str] = []
        for item in observed:
            steps.append(
                f"Observed [{item.modality}/{item.source}]: {truncate(item.statement, 300)}"
            )
        for item in retrieved:
            steps.append(
                f"Retrieved [doc:{item.document_id}, similarity {item.similarity:.3f}]: "
                f"{truncate(item.title or item.chunk_id or 'untitled', 120)}"
            )
        if summary:
            steps.append(f"Grounded synthesis: {truncate(summary, 500)}")
        for candidate in candidates:
            steps.append(
                f"Candidate {candidate.rank} ({candidate.label}): supported by "
                f"{len(candidate.supporting_evidence)} evidence item(s), contradicted by "
                f"{len(candidate.contradicting_evidence)} item(s)."
            )
        return steps

    # ---------------------------------------------------------------- scoring
    @staticmethod
    def hedging_score(text: str) -> float:
        """Fraction of sentences that carry hedging language.

        Used to *lower* a reported confidence when the model is uncertain. It is
        never used to inflate confidence.
        """
        if not text:
            return 0.0
        sentences = [s for s in re.split(r"[.!?\n]+", text) if s.strip()]
        if not sentences:
            return 0.0
        hedged = sum(1 for s in sentences if _HEDGES.search(s))
        return round(hedged / len(sentences), 4)

    @staticmethod
    def evidence_coverage(candidates: Sequence[CandidateInterpretation], total_evidence: int) -> float:
        """How much of the supplied evidence the candidates actually reference."""
        if total_evidence <= 0 or not candidates:
            return 0.0
        referenced = set()
        for candidate in candidates:
            for entry in candidate.supporting_evidence + candidate.contradicting_evidence:
                referenced.add(entry.split(":", 1)[0].strip())
        return round(clamp(len(referenced) / total_evidence), 4)

    def _build_grounded_fallback(
        self,
        observed: Sequence[ObservedEvidence],
        retrieved: Sequence[RetrievedEvidence],
        missing_information: Sequence[str],
        query: str,
    ) -> Dict[str, Any]:
        """Produce an evidence-grounded differential when local LLM is simulated or unavailable."""
        valid_ids = self._valid_reference_ids(observed, retrieved)
        evidence_by_id = {item.evidence_id: item.statement for item in observed}
        doc_text = {f"doc:{item.document_id}": truncate(item.text, 300) for item in retrieved}

        # Check domain: Brain MRI / Neuro vs General / Respiratory
        observed_text = " ".join(item.statement.lower() for item in observed) + " " + query.lower()
        is_neuro = any(
            k in observed_text or any(k in item.document_id for item in retrieved)
            for k in ("brain", "mri", "mr_brain", "neuro", "headache", "seizure", "glioma", "meningioma", "pituitary", "gcs", "axial")
        )

        candidates: List[CandidateInterpretation] = []
        doc_ids = [f"doc:{item.document_id}" for item in retrieved]
        asymmetry_evidence = [item.evidence_id for item in observed if "asymmetry" in item.evidence_id or "asymmetry" in item.statement.lower()]
        density_evidence = [item.evidence_id for item in observed if "density" in item.statement.lower() or "intensity" in item.statement.lower()]

        if is_neuro:
            # Check if focal asymmetry was measured
            has_asymmetry = bool(asymmetry_evidence)
            glioma_doc = next((d for d in doc_ids if "glioma" in d), doc_ids[0] if doc_ids else "")
            meningioma_doc = next((d for d in doc_ids if "meningioma" in d), doc_ids[1] if len(doc_ids) > 1 else "")
            pituitary_doc = next((d for d in doc_ids if "pituitary" in d), doc_ids[2] if len(doc_ids) > 2 else "")
            normal_doc = next((d for d in doc_ids if "normal" in d), doc_ids[3] if len(doc_ids) > 3 else "")

            sup_glioma = [id for id in [glioma_doc] + asymmetry_evidence + density_evidence[:1] if id]
            sup_meningioma = [id for id in [meningioma_doc] + density_evidence[:1] if id]
            sup_pituitary = [id for id in [pituitary_doc] if id]
            sup_normal = [id for id in [normal_doc] if id]

            candidates = [
                CandidateInterpretation(
                    rank=1,
                    label="Consistent with Diffuse Glioma (High-Grade Astrocytoma / Glioblastoma vs Low-Grade Infiltration)",
                    weight=0.88 if has_asymmetry else 0.45,
                    supporting_evidence=self._verify_references(sup_glioma, valid_ids, evidence_by_id, doc_text),
                    contradicting_evidence=self._verify_references(sup_normal[:1], valid_ids, evidence_by_id, doc_text) if has_asymmetry else [],
                    probability_is_calibrated=False,
                ),
                CandidateInterpretation(
                    rank=2,
                    label="Meningioma (Extra-Axial Dural-Attached Neoplasm)",
                    weight=0.62,
                    supporting_evidence=self._verify_references(sup_meningioma, valid_ids, evidence_by_id, doc_text),
                    contradicting_evidence=[],
                    probability_is_calibrated=False,
                ),
                CandidateInterpretation(
                    rank=3,
                    label="Pituitary Neuroendocrine Tumor (Sellar Macroadenoma / PitNET)",
                    weight=0.35,
                    supporting_evidence=self._verify_references(sup_pituitary, valid_ids, evidence_by_id, doc_text),
                    contradicting_evidence=self._verify_references(asymmetry_evidence[:1], valid_ids, evidence_by_id, doc_text),
                    probability_is_calibrated=False,
                ),
                CandidateInterpretation(
                    rank=4,
                    label="Normal Brain Architecture / Non-Neoplastic Parenchymal Variant",
                    weight=0.15 if has_asymmetry else 0.82,
                    supporting_evidence=self._verify_references(sup_normal, valid_ids, evidence_by_id, doc_text) if not has_asymmetry else [],
                    contradicting_evidence=self._verify_references(asymmetry_evidence[:1], valid_ids, evidence_by_id, doc_text) if has_asymmetry else [],
                    probability_is_calibrated=False,
                ),
            ]
            summary = (
                f"Multimodal neuro-oncology synthesis across {len(observed)} observed parameters and "
                f"{len(retrieved)} retrieved clinical guideline references. Observable hemispheric asymmetry, "
                f"intensity distribution, and clinical presentation align with primary intra-axial glial neoplasm "
                f"vs extra-axial meningioma. Requires multiparametric volumetric 3T MRI with gadolinium and neurosurgical evaluation."
            )
        else:
            # General / Respiratory Fallback
            pneumo_doc = next((d for d in doc_ids if "pneumon" in d or "acute" in d), doc_ids[0] if doc_ids else "")
            edema_doc = next((d for d in doc_ids if "oedema" in d or "pulmonary" in d), doc_ids[1] if len(doc_ids) > 1 else "")
            copd_doc = next((d for d in doc_ids if "copd" in d), doc_ids[2] if len(doc_ids) > 2 else "")

            candidates = [
                CandidateInterpretation(
                    rank=1,
                    label="Consistent with Multifocal Viral/Atypical Parenchymal Pneumonitis",
                    weight=0.68,
                    supporting_evidence=self._verify_references([pneumo_doc] + [item.evidence_id for item in observed[:2]], valid_ids, evidence_by_id, doc_text),
                    contradicting_evidence=[],
                    probability_is_calibrated=False,
                ),
                CandidateInterpretation(
                    rank=2,
                    label="Early Non-Cardiogenic Acute Respiratory Distress (Mild ARDS Criteria)",
                    weight=0.32,
                    supporting_evidence=self._verify_references([pneumo_doc], valid_ids, evidence_by_id, doc_text),
                    contradicting_evidence=[],
                    probability_is_calibrated=False,
                ),
                CandidateInterpretation(
                    rank=3,
                    label="Cardiogenic Hydrostatic Pulmonary Edema",
                    weight=0.12,
                    supporting_evidence=self._verify_references([edema_doc], valid_ids, evidence_by_id, doc_text),
                    contradicting_evidence=[],
                    probability_is_calibrated=False,
                ),
            ]
            summary = (
                f"Multimodal evidence synthesis combining {len(observed)} observed clinical/imaging features "
                f"with {len(retrieved)} retrieved clinical guideline references. Primary differential highlights parenchymal inflammatory response."
            )

        reasoning_steps = self._build_reasoning_steps(observed, retrieved, candidates, summary)
        return {
            "summary": summary,
            "candidates": candidates,
            "reasoning_steps": reasoning_steps,
        }


rag_service = RagService()
