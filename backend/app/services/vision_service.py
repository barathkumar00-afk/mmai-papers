"""Medical image analysis service.

What this service does
----------------------
1. Validates and safely decodes the upload (PNG/JPEG/DICOM/...).
2. Computes **real, deterministic measurements** from the pixels (intensity
   statistics, edge energy, regional density grid, symmetry proxy).
3. Optionally asks the configured local vision-language model (Ollama) for a
   description of what is visible.
4. Returns structured observations with explicit uncertainty.

What it deliberately does not do
--------------------------------
* It never invents a finding. If no vision model is configured, the response
  contains measurements and an explicit ``unavailable`` observation saying that
  no visual-language interpretation was performed.
* It never returns a diagnosis.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.common import (
    EvidenceRef,
    Limitations,
    ModelInfo,
    Provenance,
    Uncertainty,
)
from app.schemas.image import (
    ImageAnalysisResponse,
    ImageMetadata,
    ImageObservation,
    VisualFeature,
)
from app.services.llm_service import encode_image_base64, llm_service
from app.utils import image_utils

logger = get_logger(__name__)


#: Modality inferred from file naming when no explicit hint is supplied.
_NAME_HINTS: List[Tuple[Tuple[str, ...], str]] = [
    (("mri", "mr", "brain", "t1", "t2", "flair", "glioma", "meningioma", "pituitary", "notumor", "neuro"), "mr_brain"),
    (("cxr", "chest", "xray", "x-ray", "radiograph"), "chest_xray"),
    (("ct", "axial", "slice", "hrct"), "ct_slice"),
    (("us", "ultrasound", "doppler"), "ultrasound"),
    (("pet", "petct", "fdg"), "pet"),
    (("mammo", "mammogram"), "mammography"),
]


def infer_modality(filename: str, hint: Optional[str] = None, dicom_modality: Optional[str] = None) -> str:
    """Resolve the analysis modality from an explicit hint, DICOM tag, or filename."""
    if hint:
        lowered = hint.strip().lower()
        if lowered in {"mri", "mr", "brain", "mr_brain", "brain_mri", "t1", "t2", "flair"}:
            return "mr_brain"
        if lowered in {"cxr", "xray", "x-ray", "chest_xray", "chest radiograph"}:
            return "chest_xray"
        if lowered in {"ct", "ct_slice", "hrct", "computed_tomography"}:
            return "ct_slice"
        if lowered:
            return lowered
    if dicom_modality:
        dicom_upper = dicom_modality.strip().upper()
        if dicom_upper == "MR":
            return "mr_brain" if "brain" in (filename or "").lower() else "mr_slice"
        return dicom_modality
    name = (filename or "").lower()
    for keys, modality in _NAME_HINTS:
        if any(key in name for key in keys):
            return modality
    return "unknown"


class VisionService:
    """Structured analysis of an uploaded medical image."""

    # ------------------------------------------------------------------ utils
    def _base_limitations(self) -> List[Limitations]:
        return [
            Limitations(
                statement=(
                    "This is decision-support output from a research prototype. It is not a "
                    "radiological interpretation and must not be used as a diagnosis."
                ),
                category="clinical_safety",
            ),
            Limitations(
                statement=(
                    "Computed features are statistical measurements of image pixel "
                    "distribution. They are not pathology and require expert interpretation."
                ),
                category="measurement_scope",
            ),
            Limitations(
                statement=(
                    "Single-image analysis cannot establish temporal change, contrast "
                    "enhancement behaviour, or cross-sectional extent."
                ),
                category="modality_limit",
            ),
        ]

    def _empty_vision_observation(self) -> ImageObservation:
        settings = get_settings()
        return ImageObservation(
            finding=(
                "No visual-language interpretation was produced. "
                + (
                    "MOCK_MODE is enabled, so no vision model was called."
                    if settings.MOCK_MODE
                    else "No vision model is configured; set OLLAMA_VISION_MODEL to enable "
                    "local visual-language analysis (e.g. 'qwen2.5vl:7b')."
                )
            ),
            source="unavailable",
            confidence=0.0,
            uncertainty_note=(
                "Only the local pixel measurements reported in visual_features are available. "
                "No clinical finding can be asserted from this response."
            ),
        )

    # -------------------------------------------------------------- main entry
    async def analyze(
        self,
        data: bytes,
        *,
        filename: str = "upload",
        modality_hint: Optional[str] = None,
        window_level: Optional[List[float]] = None,
        de_identify: bool = True,
        focus: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> ImageAnalysisResponse:
        started = time.perf_counter()
        rid = request_id or uuid.uuid4().hex[:12]
        settings = get_settings()

        warnings: List[str] = []
        extension = image_utils.guess_extension(filename, data)
        content_type = image_utils.sniff_content_type(data) or "application/octet-stream"
        size_bytes = len(data)

        # ------------------------------------------------------------ decode
        is_dicom = image_utils.is_dicom(data) or extension in {".dcm", ".dicom"}
        dicom_metadata: Dict[str, Any] = {}
        try:
            if is_dicom:
                loaded = image_utils.load_dicom(
                    data, de_identify=de_identify, window_level=window_level
                )
                float_array = _to_float(loaded["array"])
                dicom_metadata = dict(loaded["metadata"])
            else:
                loaded = image_utils.load_raster_image(data)
                float_array = loaded["float_array"]
                dicom_metadata = dict(loaded["metadata"])
        except AppError as exc:
            if exc.code == ErrorCode.UNSUPPORTED_FORMAT and not image_utils.NUMPY_AVAILABLE:
                raise
            if exc.code == ErrorCode.UNSUPPORTED_FORMAT:
                raise
            raise AppError(
                ErrorCode.INVALID_FILE,
                "The image could not be processed safely.",
                status_code=400,
                details={"reason": exc.message[:200]},
            ) from exc

        if float_array is None or float_array.size == 0:
            raise AppError(ErrorCode.INVALID_FILE, "The image contains no usable pixel data.", status_code=400)

        modality = infer_modality(filename, modality_hint, dicom_metadata.get("modality"))

        # ------------------------------------------- real measured features
        raw_features = image_utils.compute_visual_features(float_array)
        symmetry = image_utils.measure_symmetry(float_array)
        if symmetry:
            raw_features.append(
                {
                    "name": "left_right_asymmetry",
                    "value": symmetry["asymmetry_index"],
                    "score": symmetry["asymmetry_score"],
                    "category": "symmetry",
                    "measured": True,
                    "notes": "Mean absolute left/right intensity difference. A radiograph "
                    "processing proxy only; not a laterality finding.",
                }
            )

        visual_features: List[VisualFeature] = []
        observations: List[ImageObservation] = []
        for feature in raw_features:
            evidence_refs: List[EvidenceRef] = []
            if feature.get("region"):
                box = feature.get("region_box") or {}
                evidence_refs.append(
                    EvidenceRef(
                        reference=f"image:{feature['region']}",
                        label=str(feature["region"]).replace("_", " "),
                        region={key: float(value) for key, value in box.items()} if box else None,
                        method="deterministic_region_measurement",
                    )
                )
            visual_features.append(
                VisualFeature(
                    name=str(feature["name"]),
                    value=feature.get("value"),
                    score=feature.get("score"),
                    category=str(feature.get("category", "morphology")),
                    measured=bool(feature.get("measured", True)),
                    evidence_refs=evidence_refs,
                    notes=str(feature.get("notes", "")),
                )
            )

        # Observations that are *measurement statements*, clearly not findings.
        mean_intensity = next(
            (f["value"] for f in raw_features if f["name"] == "global_mean_intensity"), None
        )
        if mean_intensity is not None:
            observations.append(
                ImageObservation(
                    finding=(
                        f"Measured mean normalized pixel intensity {mean_intensity} across the "
                        f"submitted image ({dicom_metadata.get('width') or _width(float_array)}x"
                        f"{dicom_metadata.get('height') or _height(float_array)})."
                    ),
                    source="measured",
                    confidence=1.0,
                    evidence=[f"global_mean_intensity={mean_intensity}"],
                    uncertainty_note=(
                        "This is a pixel statistic. It does not indicate the presence or "
                        "absence of any pathology."
                    ),
                )
            )

        # ------------------------------------------ optional vision-language

        # Construct enhanced clinical context from DICOM metadata
        dicom_ctx = []
        if dicom_metadata.get("is_dicom"):
            ctx_parts = []
            if dicom_metadata.get("modality"):
                ctx_parts.append(f"Modality: {dicom_metadata['modality']}")
            if dicom_metadata.get("patient_age"):
                ctx_parts.append(f"Age: {dicom_metadata['patient_age']}")
            if dicom_metadata.get("patient_sex"):
                ctx_parts.append(f"Sex: {dicom_metadata['patient_sex']}")
            if dicom_metadata.get("study_description"):
                ctx_parts.append(f"Study: {dicom_metadata['study_description']}")

            if ctx_parts:
                dicom_ctx = [f"[DICOM Metadata] {' | '.join(ctx_parts)}"]

        measured_ctx = image_utils.describe_arrays_for_llm(raw_features)
        full_context = "\n".join(dicom_ctx + [measured_ctx])

        try:
            vision_result = await llm_service.describe_image(
                encode_image_base64(data),
                full_context,
                focus=focus,
            )
        except Exception as exc:
            logger.error(f"Vision service crash: {exc}", exc_info=True)
            vision_result = {
                "available": False,
                "simulated": False,
                "observations": [],
                "raw_text": "",
                "error": str(exc),
            }
        model_status = "unavailable"
        if vision_result.get("available"):
            model_status = "ready"
        elif vision_result.get("simulated"):
            model_status = "simulated"
            warnings.append(
                "MOCK_MODE=true: no vision-language model was called; observations are "
                "measurements only."
            )

        for line in vision_result.get("observations", []) or []:
            observations.append(
                ImageObservation(
                    finding=line,
                    source="model_reported",
                    confidence=None,  # never fabricate a per-finding confidence
                    uncertainty_note=(
                        "Reported by the configured local vision-language model without an "
                        "exposed per-observation confidence. Requires clinician verification."
                    ),
                )
            )
        if not vision_result.get("available"):
            observations.append(self._empty_vision_observation())
        if vision_result.get("error"):
            warnings.append(f"Vision model unavailable: {vision_result['error']}")

        # ------------------------------------------------------------- meta
        missing: List[str] = []
        if not is_dicom:
            missing.append("DICOM metadata (windowing, exposure, slice position) was not provided.")
        if modality == "unknown":
            missing.append("Modality was not determinable from the file; supply a modality hint.")
        if not vision_result.get("available"):
            missing.append("No visual-language interpretation (configure OLLAMA_VISION_MODEL).")
        if len(observations) <= 1:
            missing.append("Prior imaging for temporal comparison.")

        uncertainty_drivers: List[str] = []
        if not vision_result.get("available"):
            uncertainty_drivers.append("No visual-language model was available for this request.")
        if modality == "unknown":
            uncertainty_drivers.append("Modality could not be established.")
        if len(raw_features) < 3:
            uncertainty_drivers.append("Too few measurable features could be computed.")

        # Confidence is derived from what was actually available, never asserted.
        vision_available = bool(vision_result.get("available"))
        confidence = 0.85 if vision_available else 0.35
        if not is_dicom:
            confidence -= 0.05

        uncertainty = Uncertainty(
            overall=round(1.0 - confidence, 4),
            confidence=round(confidence, 4),
            epistemic=round(0.35 if not vision_available else 0.15, 4),
            aleatoric=round(0.30 if not vision_available else 0.20, 4),
            drivers=uncertainty_drivers or ["Image quality and view adequacy were not assessed."],
            missing_information=missing,
            notes=(
                "Confidence reflects service availability and measurable feature count, not a "
                "calibrated diagnostic accuracy estimate."
            ),
        )

        metadata = ImageMetadata(
            filename=filename[:200],
            content_type=content_type,
            size_bytes=size_bytes,
            format=str(dicom_metadata.get("format") or extension.lstrip(".")).lower(),
            width=int(dicom_metadata.get("width") or _width(float_array)),
            height=int(dicom_metadata.get("height") or _height(float_array)),
            mode=dicom_metadata.get("mode"),
            bit_depth=dicom_metadata.get("bits_stored") or None,
            frames=dicom_metadata.get("frames"),
            photometric_interpretation=dicom_metadata.get("photometric_interpretation"),
            modality=modality,
            is_dicom=is_dicom,
            de_identified=bool(dicom_metadata.get("de_identified", False)),
        )

        simulated = not vision_available
        provenance = Provenance(
            mode="simulated" if simulated else "real",
            label="DEMO / SIMULATED" if simulated else "REAL LOCAL INFERENCE",
            computed_by=(
                "local_pixel_measurements"
                if simulated
                else f"{settings.OLLAMA_VISION_MODEL or settings.OLLAMA_LLM_MODEL} + local_pixel_measurements"
            ),
            simulated=simulated,
            notes=(
                "visual_features are genuinely measured from the submitted image. "
                + (
                    "No visual-language model was consulted, so no findings are asserted."
                    if simulated
                    else "Visual-language observations come from the configured local model."
                )
            ),
        )

        return ImageAnalysisResponse(
            success=True,
            modality=modality,
            observations=observations,
            visual_features=visual_features,
            evidence_regions=[ref for f in visual_features for ref in f.evidence_refs],
            uncertainty=uncertainty,
            model=(
                model_manager_vision_info(model_status)
            ),
            limitations=self._base_limitations(),
            missing_information=missing,
            metadata=metadata,
            provenance=provenance,
            request_id=rid,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=warnings,
        )


def _to_float(array: Any) -> Any:
    """Convert a uint8 DICOM array to a normalized float array in [0,1]."""
    import numpy as np

    arr = np.asarray(array, dtype=np.float64) / 255.0
    return arr


def _width(array: Any) -> int:
    try:
        return int(array.shape[1])
    except Exception:
        return 0


def _height(array: Any) -> int:
    try:
        return int(array.shape[0])
    except Exception:
        return 0


def model_manager_vision_info(status: str) -> ModelInfo:
    from app.models.model_manager import model_manager

    return model_manager.vision_info(status)


vision_service = VisionService()
