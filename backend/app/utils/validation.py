"""Request validation helpers: clinical parsing, numerics, text utilities."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings

_NUM_RE = re.compile(r"[-+]?\d{1,3}(?:[ ,]\d{3})*(?:\.\d+)?|[-+]?\d*\.?\d+")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")

#: Reference ranges used only to *flag* values as outside a broad adult range.
#: These are displayed as flags for clinician review, never as a diagnosis.
REFERENCE_RANGES: Dict[str, Tuple[float, float, str]] = {
    "spo2": (92.0, 100.0, "%"),
    "sao2": (92.0, 100.0, "%"),
    "crp": (0.0, 5.0, "mg/L"),
    "pct": (0.0, 5.0, "mg/L"),
    "hb": (12.0, 17.5, "g/dL"),
    "hemoglobin": (12.0, 17.5, "g/dL"),
    "wbc": (4.0, 11.0, "10^3/uL"),
    "platelets": (150.0, 400.0, "10^3/uL"),
    "plts": (150.0, 400.0, "10^3/uL"),
    "hr": (60.0, 100.0, "bpm"),
    "heart_rate": (60.0, 100.0, "bpm"),
    "sbp": (90.0, 140.0, "mmHg"),
    "dbp": (60.0, 90.0, "mmHg"),
    "rr": (12.0, 20.0, "breaths/min"),
    "resp_rate": (12.0, 20.0, "breaths/min"),
    "temperature": (36.1, 37.5, "C"),
    "temp": (36.1, 37.5, "C"),
    "spo2_room_air": (92.0, 100.0, "%"),
    "fio2": (0.21, 1.0, "ratio"),
    "bnp": (0.0, 100.0, "pg/mL"),
    "troponin": (0.0, 0.04, "ng/mL"),
    "lactate": (0.5, 2.2, "mmol/L"),
    "creatinine": (0.6, 1.3, "mg/dL"),
    "inr": (0.8, 1.2, "ratio"),
    "pao2": (80.0, 100.0, "mmHg"),
    "gcs": (13.0, 15.0, "score"),
    "glasgow_coma_scale": (13.0, 15.0, "score"),
    "kps": (70.0, 100.0, "%"),
    "karnofsky": (70.0, 100.0, "%"),
    "icp": (5.0, 15.0, "mmHg"),
    "prolactin": (2.0, 25.0, "ng/mL"),
}

#: Symptom lexicon used for deterministic feature extraction. The patterns match
#: surface text only; nothing is inferred beyond an explicit mention.
SYMPTOM_LEXICON: Dict[str, List[str]] = {
    "headache": [r"\bheadache\w*\b", r"\bcephalea\b", r"\bmigraine\b", r"\bcranial pain\b"],
    "seizure": [r"\bseizure\w*\b", r"\bepilep\w*\b", r"\bconvulsion\w*\b", r"\bictus\b", r"\bfocal twitching\b"],
    "visual_disturbance": [r"\bvisual\b", r"\bblurr(?:ed|y)\b", r"\bdiplopia\b", r"\bdouble vision\b", r"\bhemianop\w*\b", r"\bvision loss\b"],
    "focal_weakness": [r"\bweakness\b", r"\bhemiparesis\b", r"\bhemiplegia\b", r"\bfacial droop\b", r"\bnumbness\b", r"\bataxia\b"],
    "altered_mental_status": [r"\baltered mental\b", r"\bletharg\w*\b", r"\bstupor\b", r"\bsomnolen\w*\b", r"\bdisorient\w*\b", r"\baphasia\b", r"\bdysphasia\b"],
    "dyspnea": [r"\bdyspn[oe]a\b", r"\bshort(?:ness)? of breath\b", r"\bcan'?t catch my breath\b", r"\bbreathless\w*\b"],
    "orthopnea": [r"\borthopn[ae]a\b", r"\bcan'?t catch my breath when (?:lying|sitting) down\b", r"\bpropped up\b", r"\bsleeping upright\b"],
    "cough": [r"\bcough(?:ing)?\b"],
    "productive_cough": [r"\bproductive cough\b", r"\bcoughing (?:up|out)\b"],
    "fever": [r"\bfever\b", r"\bfeverish\b"],
    "chest_pain": [r"\bchest pain\b", r"\bchest tightness\b", r"\btight(?:ness)? in (?:my|the) chest\b"],
    "fatigue": [r"\bfatigue\b", r"\bexhausted\b", r"\btired\b", r"\blethargy\b"],
    "hemoptysis": [r"\bhemoptysis\b", r"\bcoughing (?:up )?blood\b"],
    "wheeze": [r"\bwheez\w*\b"],
    "stridor": [r"\bstridor\b", r"\bnoisy breathing\b", r"\bhigh[- ]pitched (?:breath|noise)\w*\b"],
    "palpitations": [r"\bpalpitation\w*\b", r"\bheart (?:racing|fluttering)\b"],
    "edema": [r"\bo?edema\b", r"\bswollen (?:ankles|feet|legs)\b"],
    "confusion": [r"\bconfus\w+\b", r"\bdisorient\w+\b"],
}

_DURATION_RE = re.compile(r"\b(\d+)\s*(day|days|hour|hours|week|weeks|month|months)\b", re.IGNORECASE)


def extract_number(value: Any) -> Optional[float]:
    """Best-effort numeric extraction from a messy clinical string."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    percent = _PERCENT_RE.search(text)
    if percent:
        return float(percent.group(1))
    match = _NUM_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def classify_direction(name: str, value: Optional[float]) -> Tuple[Optional[bool], Optional[str], str]:
    """Compare a value against a broad reference range.

    Returns ``(abnormal, direction, unit)``. The result is a *flag for review*,
    not a clinical judgement.
    """
    key = normalize_key(name)
    entry = REFERENCE_RANGES.get(key)
    if entry is None or value is None:
        return None, None, ""
    low, high, unit = entry
    if value < low:
        return True, "low", unit
    if value > high:
        return True, "high", unit
    return False, "normal", unit


def detect_symptoms(text: str) -> List[Dict[str, Any]]:
    """Return symptoms that are *explicitly mentioned* in the text."""
    if not text:
        return []
    lowered = text.lower()
    found: List[Dict[str, Any]] = []
    for symptom, patterns in SYMPTOM_LEXICON.items():
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                start = max(match.start() - 40, 0)
                end = min(match.end() + 40, len(text))
                found.append(
                    {
                        "name": symptom,
                        "matched_text": text[start:end].strip(),
                        "pattern": pattern,
                    }
                )
                break
    return found


def extract_durations(text: str) -> List[Dict[str, str]]:
    """Extract explicit time expressions, e.g. '48 hours' -> 2 days."""
    if not text:
        return []
    results: List[Dict[str, str]] = []
    for match in _DURATION_RE.finditer(text):
        amount = int(match.group(1))
        unit = match.group(2).lower().rstrip("s")
        days = {
            "day": 1,
            "hour": 1 / 24,
            "week": 7,
            "month": 30,
        }.get(unit, 1)
        results.append(
            {
                "raw": match.group(0),
                "amount": str(amount),
                "unit": unit,
                "days": f"{amount * days:.2f}",
            }
        )
    return results


#: Alias kept for readability at call sites that talk about "detecting" durations.
detect_durations = extract_durations


def detect_negations(text: str) -> List[str]:
    """Very small surface-negation detector for evidence qualification."""
    if not text:
        return []
    return [match.group(0).strip().lower() for match in re.finditer(r"\b(?:no|not|without|denies|negative)\b", text, re.IGNORECASE)]


def split_sentences(text: str) -> List[str]:
    """Sentence splitter that also breaks on newlines and semicolons."""
    if not text:
        return []
    normalized = re.sub(r"\s+", " ", text.replace("\n", ". ").replace(";", ". "))
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def sanitize_text_payload(payload: Dict[str, Any], max_items: int = 200) -> Dict[str, Any]:
    """Bound the size of arbitrary dicts before they reach a prompt."""
    cleaned: Dict[str, Any] = {}
    for index, (key, value) in enumerate(payload.items()):
        if index >= max_items:
            break
        if isinstance(value, str):
            cleaned[str(key)] = truncate(value, 500)
        elif isinstance(value, (int, float, bool)) or value is None:
            cleaned[str(key)] = value
        elif isinstance(value, (list, tuple)):
            cleaned[str(key)] = [truncate(str(v), 200) for v in list(value)[:50]]
        elif isinstance(value, dict):
            cleaned[str(key)] = sanitize_text_payload(dict(value), max_items=25)
        else:
            cleaned[str(key)] = truncate(str(value), 200)
    return cleaned


def enforce_text_limit(text: str) -> str:
    limit = get_settings().MAX_CLINICAL_TEXT_CHARS
    return truncate(text or "", limit)


def require_non_empty(values: Dict[str, Any], field_name: str = "request") -> None:
    if not any(str(v).strip() for v in values.values() if v is not None):
        from app.core.errors import AppError, ErrorCode

        raise AppError(
            ErrorCode.MISSING_PARAMETER,
            f"At least one {field_name} field is required.",
            status_code=400,
            details={"received_fields": sorted(values.keys())},
        )


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out
