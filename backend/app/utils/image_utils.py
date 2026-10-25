"""Safe image and DICOM processing helpers.

All heavy imaging dependencies (Pillow, pydicom, NumPy) are imported lazily and
guarded so the API still starts when they are not installed -- it simply reports
the dependency as unavailable instead of crashing.
"""

from __future__ import annotations

import base64
import binascii
import io
import math
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.security import guess_extension, is_dicom, sniff_content_type

try:  # pragma: no cover - import guard
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None  # type: ignore[assignment]

try:  # pragma: no cover - import guard
    from PIL import Image as _PILImage
except Exception:  # pragma: no cover
    _PILImage = None  # type: ignore[assignment]

try:  # pragma: no cover - import guard
    import pydicom as _pydicom
except Exception:  # pragma: no cover
    _pydicom = None  # type: ignore[assignment]

PIL_AVAILABLE = _PILImage is not None
NUMPY_AVAILABLE = _np is not None
DICOM_AVAILABLE = _pydicom is not None

#: DICOM attributes removed by default to avoid retaining patient identifiers.
DEFAULT_DEIDENTIFY_TAGS: Tuple[str, ...] = (
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "AccessionNumber",
    "InstitutionName",
    "InstitutionAddress",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "OperatorsName",
    "StudyDate",
    "StudyTime",
    "SeriesDate",
    "AcquisitionDate",
    "ContentDate",
    "ContentTime",
)


def dependency_status() -> Dict[str, bool]:
    return {
        "pillow": PIL_AVAILABLE,
        "numpy": NUMPY_AVAILABLE,
        "pydicom": DICOM_AVAILABLE,
    }


def decode_base64_image(payload: str) -> bytes:
    """Decode a base64 string that may carry a data-URI prefix."""
    if not payload:
        raise AppError(ErrorCode.INVALID_FILE, "Empty base64 image payload.", status_code=400)
    raw = payload.strip()
    if raw.startswith("data:"):
        _, _, raw = raw.partition(",")
    raw = raw.replace("\n", "").replace("\r", "").replace(" ", "")
    try:
        return base64.b64decode(raw, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise AppError(
            ErrorCode.INVALID_FILE, "Image payload is not valid base64.", status_code=400
        ) from exc


def apply_dicom_windowing(array: Any, center: float, width: float) -> Any:
    """Apply a standard linear DICOM window (WC / WW) to a float array."""
    if _np is None:
        return array
    lower = center - width / 2.0
    upper = center + width / 2.0
    return _np.clip((array - lower) / max(width, 1e-6), 0.0, 1.0)


def normalize_array(array: Any) -> Any:
    """Min-max normalize to [0, 1]; returns None for constant arrays."""
    if _np is None:
        return None
    arr = _np.asarray(array, dtype=_np.float64)
    lo, hi = float(_np.min(arr)), float(_np.max(arr))
    if math.isclose(lo, hi):
        return _np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def infer_modality_from_dicom(dataset: Any) -> Optional[str]:
    """Best-effort modality guess from standard DICOM attributes."""
    if dataset is None:
        return None
    modality = str(getattr(dataset, "Modality", "") or "").strip().upper()
    if modality in {"CR", "DX", "DR", "RF", "RG", "MG", "NM"}:
        return "chest_xray"
    if modality == "CT":
        body_part = str(getattr(dataset, "BodyPartExamined", "") or "").upper()
        if "CHEST" in body_part or "THORAX" in body_part or "LUNG" in body_part:
            return "ct_slice"
        return "ct_slice"
    if modality == "MR":
        return "mr_slice"
    if modality in {"US", "XA"}:
        return "ultrasound"
    if modality == "PT":
        return "pet"
    return None


def load_dicom(
    data: bytes, *, de_identify: bool = True, window_level: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Parse a DICOM payload into a displayable 8-bit array plus metadata.

    Returns a dict with ``array`` (NumPy 2-D uint8), ``metadata`` and
    ``de_identified``. Raises :class:`AppError` when pydicom/numpy are missing.
    """
    if not DICOM_AVAILABLE:
        raise AppError(
            ErrorCode.UNSUPPORTED_FORMAT,
            "DICOM processing requires the 'pydicom' package to be installed.",
            status_code=415,
        )
    if _np is None:
        raise AppError(
            ErrorCode.INTERNAL_ERROR, "DICOM processing requires NumPy.", status_code=500
        )

    try:
        dataset = _pydicom.dcmread(io.BytesIO(data), force=True)
    except Exception as exc:  # pragma: no cover - defensive
        raise AppError(ErrorCode.INVALID_FILE, f"DICOM could not be parsed: {exc}", status_code=400) from exc

    # Extract native windowing before de-identification
    native_center = getattr(dataset, "WindowCenter", None)
    native_width = getattr(dataset, "WindowWidth", None)

    # Handle cases where window center/width are lists (multiple windows)
    if isinstance(native_center, _np.ndarray) or isinstance(native_center, list):
        native_center = native_center[0]
    if isinstance(native_width, _np.ndarray) or isinstance(native_width, list):
        native_width = native_width[0]

    de_identified = False
    if de_identify:
        for tag in DEFAULT_DEIDENTIFY_TAGS:
            if tag in dataset:
                del dataset[tag]
        dataset.PatientName = "ANONYMOUS"
        dataset.PatientID = "ANONYMOUS"
        de_identified = True

    try:
        array = dataset.pixel_array
    except Exception as exc:
        raise AppError(
            ErrorCode.UNSUPPORTED_FORMAT,
            "DICOM pixel data could not be decoded (compressed or unsupported transfer syntax).",
            status_code=415,
            details={"reason": str(exc)[:200]},
        ) from exc

    array = _np.asarray(array)
    metadata: Dict[str, Any] = {
        "is_dicom": True,
        "de_identified": de_identified,
        "modality": infer_modality_from_dicom(dataset),
        "photometric_interpretation": str(getattr(dataset, "PhotometricInterpretation", "") or "") or None,
        "frames": int(getattr(dataset, "NumberOfFrames", 1) or 1),
        "rows": int(getattr(dataset, "Rows", array.shape[-2]) or array.shape[-2]),
        "columns": int(getattr(dataset, "Columns", array.shape[-1]) or array.shape[-1]),
        "bits_stored": int(getattr(dataset, "BitsStored", 0) or 0),
        "series_description": str(getattr(dataset, "SeriesDescription", "") or "") or None,
        "study_description": str(getattr(dataset, "StudyDescription", "") or "") or None,
        "patient_age": str(getattr(dataset, "PatientAge", "") or ""),
        "patient_sex": str(getattr(dataset, "PatientSex", "") or ""),
        "native_window": [float(native_center), float(native_width)] if native_center is not None and native_width is not None else None,
    }

    if window_level:
        arr_float = array.astype(_np.float64)
        arr_float = apply_dicom_windowing(arr_float, float(window_level[0]), float(window_level[1]))
        array = (arr_float * 255).astype(_np.uint8)
    elif metadata["native_window"]:
        # Use native DICOM windowing if available and no override provided
        arr_float = array.astype(_np.float64)
        arr_float = apply_dicom_windowing(arr_float, metadata["native_window"][0], metadata["native_window"][1])
        array = (arr_float * 255).astype(_np.uint8)
    elif array.dtype != _np.uint8:
        array = (normalize_array(array) * 255).astype(_np.uint8)

    # Multi-frame / colour: take the first frame, collapse RGB to luminance.
    if array.ndim == 3:
        first = array[0] if array.shape[-1] not in (3, 4) else array
        if first.ndim == 3 and first.shape[-1] in (3, 4):
            array = (0.299 * first[..., 0] + 0.587 * first[..., 1] + 0.114 * first[..., 2]).astype(_np.uint8)
        else:
            array = first

    return {"array": array, "metadata": metadata, "de_identified": de_identified}


def load_raster_image(data: bytes) -> Dict[str, Any]:
    """Load PNG/JPEG/etc. via Pillow into a normalized NumPy array."""
    if not PIL_AVAILABLE or _np is None:
        raise AppError(
            ErrorCode.UNSUPPORTED_FORMAT,
            "Raster image processing requires 'Pillow' and 'NumPy' to be installed.",
            status_code=415,
        )
    try:
        with _PILImage.open(io.BytesIO(data)) as img:
            img.load()
            mode = img.mode
            width, height = img.size
            format_name = (img.format or "unknown").lower()
            converted = img.convert("L") if mode not in ("L", "I;16", "I", "F") else img
            array = _np.asarray(converted, dtype=_np.float64)
    except Exception as exc:
        raise AppError(
            ErrorCode.INVALID_FILE, f"Image could not be decoded: {exc}", status_code=400
        ) from exc

    normalized = normalize_array(array)
    if normalized is None:
        raise AppError(ErrorCode.INVALID_FILE, "Image contains no pixel variation.", status_code=400)

    return {
        "array": (normalized * 255).astype(_np.uint8),
        "float_array": normalized,
        "metadata": {
            "is_dicom": False,
            "mode": mode,
            "width": int(width),
            "height": int(height),
            "format": format_name,
        },
    }


def compute_visual_features(
    float_array: Any, *, tiles: Tuple[int, int] = (4, 4)
) -> List[Dict[str, Any]]:
    """Compute deterministic, interpretable image statistics.

    These are genuine measurements of the submitted pixels (mean intensity,
    density proxy, local edge energy) -- never invented findings. They are
    reported as ``measured`` features and never as pathology.
    """
    if _np is None or float_array is None:
        return []

    arr = _np.asarray(float_array, dtype=_np.float64)
    if arr.size == 0:
        return []

    # Low-frequency field: local mean over an 8x8 box, used for the
    # "regional density" density-proxy features.
    rows, cols = arr.shape
    tr, tc = tiles
    step_r, step_c = max(rows // tr, 1), max(cols // tc, 1)
    region_means: List[float] = []
    for r in range(tr):
        for c in range(tc):
            block = arr[r * step_r : (r + 1) * step_r, c * step_c : (c + 1) * step_c]
            if block.size:
                region_means.append(float(block.mean()))

    # Gradient magnitude (Sobel-like central differences) as an edge-energy proxy.
    if arr.shape[0] > 2 and arr.shape[1] > 2:
        gy, gx = _np.gradient(arr)
        edge_energy = float(_np.mean(_np.sqrt(gx**2 + gy**2)))
    else:
        edge_energy = 0.0

    intensity_std = float(arr.std())
    global_mean = float(arr.mean())

    features: List[Dict[str, Any]] = [
        {
            "name": "global_mean_intensity",
            "value": round(global_mean, 4),
            "score": round(global_mean, 4),
            "category": "intensity",
            "measured": True,
            "notes": "Mean normalized pixel intensity in [0,1].",
        },
        {
            "name": "intensity_std",
            "value": round(intensity_std, 4),
            "score": round(min(intensity_std * 2.0, 1.0), 4),
            "category": "contrast",
            "measured": True,
            "notes": "Standard deviation of normalized pixel intensity.",
        },
        {
            "name": "edge_energy",
            "value": round(edge_energy, 4),
            "score": round(min(edge_energy * 5.0, 1.0), 4),
            "category": "structure",
            "measured": True,
            "notes": "Mean gradient magnitude; higher values indicate more structural detail.",
        },
    ]

    if region_means:
        arr_regions = _np.asarray(region_means, dtype=_np.float64)
        features.append(
            {
                "name": "regional_density_variability",
                "value": round(float(arr_regions.std()), 4),
                "score": round(min(float(arr_regions.std()) * 3.0, 1.0), 4),
                "category": "distribution",
                "measured": True,
                "notes": "Variability of mean intensity across a "
                f"{tr}x{tc} grid of regions; a proxy for non-uniform parenchymal density.",
            }
        )
        if tr == tc == 4:
            labels = {
                0: ("left_upper", (0.0, 0.0, 0.5, 0.5)),
                1: ("right_upper", (0.5, 0.0, 0.5, 0.5)),
                2: ("left_mid", (0.0, 0.5, 0.5, 0.5)),
                3: ("center", (0.5, 0.5, 0.5, 0.5)),
                4: ("right_mid", (1.0, 0.5, 0.5, 0.5)),
                5: ("left_lower", (0.0, 1.0, 0.5, 0.5)),
                6: ("right_lower", (0.5, 1.0, 0.5, 0.5)),
                7: ("center_lower", (1.0, 1.0, 0.5, 0.5)),
            }
            for idx, (name, box) in labels.items():
                if idx < len(region_means):
                    features.append(
                        {
                            "name": f"regional_mean::{name}",
                            "value": round(region_means[idx], 4),
                            "score": round(region_means[idx], 4),
                            "category": "region_density",
                            "measured": True,
                            "region": name,
                            "region_box": box,
                            "notes": f"Mean normalized intensity of the {name.replace('_', ' ')} region.",
                        }
                    )
    return features


def measure_symmetry(float_array: Any) -> Optional[Dict[str, float]]:
    """Left/right intensity asymmetry proxy, normalized to [0,1]."""
    if _np is None or float_array is None:
        return None
    arr = _np.asarray(float_array, dtype=_np.float64)
    if arr.shape[1] < 4:
        return None
    half = arr.shape[1] // 2
    left = arr[:, :half]
    right = _np.fliplr(arr[:, half : half * 2])
    if left.size == 0 or right.size == 0:
        return None
    diff = _np.abs(left - right)
    return {
        "asymmetry_index": round(float(diff.mean()), 4),
        "asymmetry_score": round(min(float(diff.mean()) * 4.0, 1.0), 4),
    }


def describe_arrays_for_llm(features: List[Dict[str, Any]], limit: int = 20) -> str:
    """Render measured features as compact text for a vision-language prompt."""
    lines = []
    for feature in features[:limit]:
        value = feature.get("value")
        lines.append(f"- {feature.get('name')}: {value} ({feature.get('category')})")
    return "\n".join(lines) if lines else "- No measurable features were computed."
