"""Clinical text / structured data normalization service.

Produces a structured patient representation from symptoms, history, labs,
vitals, medications and free-text notes.

Every derived feature is produced by an explicit, inspectable rule over the
submitted values. Nothing is imputed, and no reference-range flag is presented
as a diagnosis.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.models.model_manager import model_manager
from app.schemas.clinical import (
    ClinicalAnalysisResponse,
    ClinicalFeature,
    ClinicalInput,
    LabValue,
    VitalSign,
)
from app.schemas.common import Limitations, Provenance, Uncertainty
from app.utils.validation import (
    classify_direction,
    dedupe_preserve_order,
    detect_durations,
    detect_symptoms,
    enforce_text_limit,
    extract_number,
    normalize_key,
    require_non_empty,
    split_sentences,
)

logger = get_logger(__name__)

#: Hard bound on a single lab/vital value's narrative representation.
_VALUE_TEXT_LIMIT = 300


class ClinicalService:
    """Normalizes heterogeneous clinical input into a structured representation."""

    # ---------------------------------------------------------------- limits
    def _limitations(self) -> List[Limitations]:
        return [
            Limitations(
                statement=(
                    "Structured flags are threshold checks against broad adult reference ranges "
                    "for triage review. They are not diagnoses and not calibrated to any "
                    "patient-specific reference interval."
                ),
                category="measurement_scope",
            ),
            Limitations(
                statement=(
                    "Missing values are reported as missing. No value is imputed or inferred."
                ),
                category="completeness",
            ),
            Limitations(
                statement=(
                    "Free-text parsing is lexical. Negations and hedging in clinical prose can "
                    "mislead surface-pattern extraction and must be verified by a clinician."
                ),
                category="nlp_limit",
            ),
        ]

    # ------------------------------------------------------------ normalizers
    def _normalize_mapping(self, raw: Dict[str, Any], kind: str) -> List[Any]:
        items: List[Any] = []
        for key, value in raw.items():
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            number = extract_number(value)
            abnormal, direction, unit = classify_direction(key, number)
            common = {
                "name": normalize_key(key) or key[:60],
                "raw": text[:_VALUE_TEXT_LIMIT],
                "value": number,
                "unit": unit or _infer_unit(text),
                "reference_range": list(_reference_for(key) or ()) or None,
                "abnormal": abnormal,
                "direction": direction,
            }
            if kind == "lab":
                items.append(LabValue(**common, source="reported"))
            else:
                items.append(VitalSign(**common, note="" if abnormal is not None else "No reference range configured."))
        return items

    def _build_features(
        self,
        *,
        text: str,
        labs: List[LabValue],
        vitals: List[VitalSign],
        symptoms: List[str],
    ) -> List[ClinicalFeature]:
        """Deterministic, fully inspectable clinical flags."""
        features: List[ClinicalFeature] = []
        lab_by_name = {lab.name: lab for lab in labs}
        vital_by_name = {vital.name: vital for vital in vitals}

        # ---- hypoxemia
        for key in ("spo2", "sao2", "spo2_room_air", "o2_saturation", "oxygen_saturation"):
            vital = vital_by_name.get(key)
            if vital and vital.value is not None and vital.value < 92.0:
                on_air = "room air" in (vital.raw or "").lower() or "ambient" in (vital.raw or "").lower()
                features.append(
                    ClinicalFeature(
                        name="hypoxemia",
                        detail=(
                            f"Reported SpO2 {vital.value}% {'on room air' if on_air else ''} "
                            f"(threshold < 92%)."
                        ),
                        inputs=[f"vitals.{key}={vital.raw}"],
                        rule="spo2 < 92",
                        confidence=1.0,
                    )
                )
                break

        # ---- PaO2/FiO2 ratio when both are present
        pao2 = lab_by_name.get("pao2") or vital_by_name.get("pao2")
        fio2 = lab_by_name.get("fio2") or vital_by_name.get("fio2")
        if pao2 and fio2 and pao2.value and fio2.value:
            ratio = pao2.value / max(fio2.value, 1e-6)
            features.append(
                ClinicalFeature(
                    name="pao2_fio2_ratio",
                    detail=f"PaO2/FiO2 = {ratio:.0f} mmHg.",
                    inputs=[f"pao2={pao2.raw}", f"fio2={fio2.raw}"],
                    rule="pao2 / max(fio2, 1e-6)",
                    confidence=1.0,
                )
            )

        # ---- systemic inflammation markers
        for key, threshold in (("crp", 5.0), ("pct", 0.5), ("esr", 20.0)):
            lab = lab_by_name.get(key)
            if lab and lab.value is not None and lab.value > threshold:
                features.append(
                    ClinicalFeature(
                        name=f"elevated_{key}",
                        detail=f"Reported {key.upper()} {lab.value} {lab.unit} (threshold > {threshold}).",
                        inputs=[f"labs.{key}={lab.raw}"],
                        rule=f"{key} > {threshold}",
                        confidence=1.0,
                    )
                )
                break

        # ---- explicit symptoms present in the text
        detected = detect_symptoms(text)
        for item in detected[:12]:
            features.append(
                ClinicalFeature(
                    name=f"reported_{item['name']}",
                    detail=f"Text mentions {item['name'].replace('_', ' ')}.",
                    inputs=[item["matched_text"][:200]],
                    rule=f"lexical match: {item['pattern']}",
                    confidence=0.85,
                )
            )

        # ---- explicit durations
        durations = detect_durations(text)
        for item in durations[:4]:
            features.append(
                ClinicalFeature(
                    name="symptom_duration",
                    detail=f"Symptoms reported for {item['raw']} (~{item['days']} days).",
                    inputs=[item["raw"]],
                    rule=r"\d+\s*(day|hour|week|month)s?",
                    confidence=1.0,
                )
            )

        # ---- out-of-range flags
        for item in list(labs) + list(vitals):
            if item.abnormal:
                features.append(
                    ClinicalFeature(
                        name=f"out_of_range_{item.name}",
                        detail=f"{item.name} {item.value} {item.unit} is outside the broad "
                        f"reference range ({'below' if item.direction == 'low' else 'above'}).",
                        inputs=[f"{item.name}={item.raw}"],
                        rule=f"{item.name} outside reference range",
                        confidence=1.0,
                    )
                )

        return features[:40]

    # ------------------------------------------------------------------ main
    async def analyze(
        self, data: ClinicalInput, *, request_id: Optional[str] = None
    ) -> ClinicalAnalysisResponse:
        started = time.perf_counter()
        rid = request_id or uuid.uuid4().hex[:12]
        settings = get_settings()

        # ------------------------------------------------- fold in workbench fields
        symptoms = dedupe_preserve_order(list(data.symptoms))
        history = dedupe_preserve_order(list(data.history))
        medications = dedupe_preserve_order(list(data.medications))
        notes = enforce_text_limit(data.clinical_notes)

        # SpO2 / CRP arriving as workbench strings belong in the vitals/labs maps.
        vitals_raw: Dict[str, Any] = dict(data.vitals)
        labs_raw: Dict[str, Any] = dict(data.labs)
        if data.spo2.strip():
            vitals_raw.setdefault("spo2", data.spo2)
        if data.crp.strip():
            labs_raw.setdefault("crp", data.crp)

        if not any([symptoms, history, medications, notes, vitals_raw, labs_raw, data.complaint, data.chief_complaint]):
            raise AppError(
                ErrorCode.MALFORMED_CLINICAL_DATA,
                "No clinical content was supplied. Provide at least one of: symptoms, history, "
                "labs, vitals, medications, clinical notes, or chief complaint.",
                status_code=400,
            )

        vitals = self._normalize_mapping(vitals_raw, "vital")
        labs = self._normalize_mapping(labs_raw, "lab")

        complaint = data.complaint or data.chief_complaint
        text = data.all_text()

        symptoms_from_text = [item["name"].replace("_", " ") for item in detect_symptoms(text)]
        symptoms = dedupe_preserve_order(symptoms + symptoms_from_text)

        clinical_features = self._build_features(
            text=text, labs=labs, vitals=vitals, symptoms=symptoms
        )

        # ------------------------------------------------ retrieval query text
        retrieval_query = self._build_retrieval_query(
            symptoms=symptoms, vitals=vitals, labs=labs, complaint=complaint
        )

        # ------------------------------------------------------------- meta
        missing: List[str] = []
        if not symptoms:
            missing.append("Explicit symptom list.")
        if not history:
            missing.append("Past medical / surgical / social history.")
        if not medications:
            missing.append("Medication and allergy list.")
        if not labs:
            missing.append("Laboratory results.")
        if not vitals:
            missing.append("Vital signs including oxygen support status.")
        if not settings.RETRIEVAL_TOP_K:
            missing.append("Retrieval configuration.")

        drivers: List[str] = []
        if not labs:
            drivers.append("No laboratory data was supplied.")
        if not vitals:
            drivers.append("No vital signs were supplied.")
        if not history:
            drivers.append("No clinical history was supplied.")
        if not drivers:
            drivers.append("Structured fields present; free-text completeness unverified.")

        completeness = 0.0
        for present, weight in ((symptoms, 0.25), (vitals, 0.25), (labs, 0.2), (history, 0.15), (medications, 0.15)):
            completeness += weight if present else 0.0
        confidence = round(0.3 + 0.5 * completeness, 4)

        uncertainty = Uncertainty(
            overall=round(1.0 - confidence, 4),
            confidence=confidence,
            epistemic=round(0.4, 4),
            aleatoric=round(0.25, 4),
            drivers=dedupe_preserve_order(drivers),
            missing_information=missing,
            notes=(
                "Confidence reflects the proportion of supplied structured fields, not a "
                "calibrated clinical accuracy estimate."
            ),
        )

        patient_representation: Dict[str, Any] = {
            "symptoms": symptoms,
            "history": history,
            "labs": {lab.name: lab.model_dump() for lab in labs},
            "vitals": {vital.name: vital.model_dump() for vital in vitals},
            "medications": medications,
            "chief_complaint": complaint,
            "clinical_notes": notes,
            "comorbidities": data.comorbidities,
            "narrative": text[:4000],
            "out_of_range": [
                item.name for item in list(labs) + list(vitals) if item.abnormal
            ],
        }

        return ClinicalAnalysisResponse(
            success=True,
            patient_representation=patient_representation,
            normalized_data=patient_representation,
            symptoms=symptoms,
            history=history,
            labs={lab.name: lab.model_dump() for lab in labs},
            vitals={vital.name: vital.model_dump() for vital in vitals},
            medications=medications,
            clinical_features=clinical_features,
            retrieval_query=retrieval_query,
            uncertainty=uncertainty,
            model=model_manager.llm_info(
                "not_required", name="rule_based_normalizer"
            ),
            limitations=self._limitations(),
            missing_information=missing,
            provenance=Provenance(
                mode="real",
                label="REAL DETERMINISTIC PROCESSING",
                computed_by="rule_based_normalizer + lexical_extraction",
                simulated=False,
                notes=(
                    "All fields are normalized deterministically from the submitted values. "
                    "No model-generated content is included at this stage."
                ),
            ),
            request_id=rid,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=(
                ["No LLM is used at this stage; clinical text is normalized deterministically."]
            ),
        )

    @staticmethod
    def _build_retrieval_query(
        *,
        symptoms: List[str],
        vitals: List[VitalSign],
        labs: List[LabValue],
        complaint: str,
    ) -> str:
        """Build the natural-language query used for FAISS retrieval."""
        parts: List[str] = []
        if complaint:
            parts.append(complaint[:400])
        if symptoms:
            parts.append("Reported symptoms: " + ", ".join(symptoms[:10]))
        abnormal_vitals = [v for v in vitals if v.abnormal]
        if abnormal_vitals:
            parts.append(
                "Abnormal vitals: "
                + ", ".join(f"{v.name} {v.value}{v.unit}" for v in abnormal_vitals[:8])
            )
        abnormal_labs = [lab for lab in labs if lab.abnormal]
        if abnormal_labs:
            parts.append(
                "Abnormal labs: "
                + ", ".join(f"{lab.name} {lab.value}{lab.unit}" for lab in abnormal_labs[:8])
            )
        return "; ".join(parts).strip() or "clinical presentation"


# ------------------------------------------------------------------- helpers
def _reference_for(key: str) -> Optional[Tuple[float, float]]:
    from app.utils.validation import REFERENCE_RANGES

    entry = REFERENCE_RANGES.get(normalize_key(key))
    return (entry[0], entry[1]) if entry else None


def _infer_unit(text: str) -> str:
    lowered = (text or "").lower()
    for unit in ("mg/l", "ng/ml", "pg/ml", "g/dl", "mmhg", "bpm", "mmol/l", "%", "celsius", "mm"):
        if unit in lowered:
            return unit
    return ""


clinical_service = ClinicalService()
