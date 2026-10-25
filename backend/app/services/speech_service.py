"""Speech and audio analysis service.

Pipeline::

    audio bytes
      -> safe decode + resample to 16 kHz mono      (utils.audio_utils)
      -> measured acoustic features                 (real signal processing)
      -> local speech recognition                   (faster-whisper / whisper.cpp)
      -> transcript-derived clinical observations   (deterministic lexicon)
      -> optional LLM structuring                   (configured local LLM)

Symptoms are never added beyond what the transcript literally contains. When no
ASR model is installed the service returns the measured acoustic features plus an
explicit ``unavailable`` observation, never a fabricated transcript.
"""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.security import secure_temp_file, sniff_content_type
from app.models.model_manager import model_manager
from app.schemas.common import Limitations, Provenance, Uncertainty
from app.schemas.speech import (
    ClinicalObservation,
    SpeechAnalysisResponse,
    SpeechFeature,
    SpeechMetadata,
    TranscriptSegment,
)
from app.services.llm_service import llm_service
from app.utils import audio_utils
from app.utils.validation import dedupe_preserve_order, detect_negations, split_sentences

logger = get_logger(__name__)

#: Surface patterns mapped to clinical categories, used only to *classify text
#: that is already present* in the transcript.
_CATEGORY_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(short(?:ness)? of breath|dyspn[oe]a|can't catch my breath|breathless)\b", "symptom:respiratory"),
    (r"\b(orthopn[ae]a|lying down|propped up|sleeping upright)\b", "symptom:positional"),
    (r"\bcough\w*\b", "symptom:cough"),
    (r"\b(fever|feverish|chills?|shivering)\b", "symptom:systemic"),
    (r"\b(chest pain|tightness in (?:my|the) chest)\b", "symptom:cardiac"),
    (r"\b(fatigue|exhausted|tired|weak)\b", "symptom:constitutional"),
    (r"\b(hemoptysis|coughing (?:up )?blood)\b", "symptom:haemoptysis"),
    (r"\b(wheez\w+|stridor|noisy breathing)\b", "symptom:airway"),
    (r"\b(palpitation\w*|heart racing)\b", "symptom:cardiac"),
    (r"\b(swollen|oedema|edema)\b", "symptom:peripheral"),
    (r"\b(confus\w+|disorient\w+)\b", "symptom:neuro"),
    (r"\b(started|since|for the (?:last|past))\b", "timeline"),
    (r"\b(nothing|no|not|never|denies)\b", "negation"),
]


class SpeechService:
    """Structured analysis of an uploaded clinical audio clip."""

    def _limitations(self) -> List[Limitations]:
        return [
            Limitations(
                statement=(
                    "This is decision-support output from a research prototype. It is not a "
                    "clinical assessment and must not be used as a diagnosis."
                ),
                category="clinical_safety",
            ),
            Limitations(
                statement=(
                    "Acoustic features are signal-processing estimates. Speech-cadence proxies "
                    "are not respiratory-rate measurements and can be confounded by recording "
                    "quality, accent, and microphone placement."
                ),
                category="measurement_scope",
            ),
            Limitations(
                statement=(
                    "Transcription of patient speech is error-prone, particularly for "
                    "breathless, quiet, or accented speech. The transcript must be verified."
                ),
                category="asr_limit",
            ),
        ]

    # ------------------------------------------------------------ ASR loading
    def _load_asr(self) -> Tuple[Optional[Any], str, str]:
        """Return ``(model, backend_name, status)`` without raising."""
        settings = get_settings()
        if settings.MOCK_MODE:
            return None, "", "simulated"

        model_path = settings.whisper_model_path
        if model_path and model_path.exists():
            instance = model_manager.singleton(
                "whisper_model",
                lambda: _load_faster_whisper(model_path, settings),
                probe=lambda: _faster_whisper_available(),
            )
            if instance is not None:
                return instance, f"faster-whisper:{model_path.name}", "loaded"
            return None, "", "unavailable"

        # Auto-discovery of a default local Whisper model (downloaded once).
        instance = model_manager.singleton(
            "whisper_auto",
            lambda: _load_faster_whisper("small", settings),
            probe=lambda: _faster_whisper_available(),
        )
        if instance is not None:
            return instance, "faster-whisper:small", "loaded"
        return None, "", "unavailable"

    async def _transcribe(
        self, model: Any, path: Path, language: Optional[str] = None
    ) -> Tuple[str, List[TranscriptSegment], Optional[float]]:
        import anyio

        def _run() -> Tuple[str, List[TranscriptSegment], Optional[float]]:
            segments_iter, info = model.transcribe(
                str(path),
                language=language,
                vad_filter=True,
                beam_size=1,
                temperature=0.0,
            )
            segments: List[TranscriptSegment] = []
            text_parts: List[str] = []
            weighted = 0.0
            total = 0.0
            for segment in segments_iter:
                piece = (getattr(segment, "text", "") or "").strip()
                if piece:
                    segments.append(
                        TranscriptSegment(
                            start=round(float(getattr(segment, "start", 0.0)), 3),
                            end=round(float(getattr(segment, "end", 0.0)), 3),
                            text=piece,
                        )
                    )
                    text_parts.append(piece)
                probability = getattr(segment, "avg_logprob", None)
                duration = max(float(getattr(segment, "end", 0.0)) - float(getattr(segment, "start", 0.0)), 0.0)
                if probability is not None:
                    weighted += float(np.exp(min(probability / 3.0, 0.0))) * duration
                    total += duration
            return " ".join(text_parts), segments, (weighted / total if total else None)

        return await anyio.to_thread.run_sync(_run)

    # -------------------------------------------------------- text processing
    @staticmethod
    def _observations_from_transcript(transcript: str) -> List[ClinicalObservation]:
        """Derive observations strictly from the words present in the transcript."""
        if not transcript.strip():
            return []
        observations: List[ClinicalObservation] = []
        seen: set[str] = set()

        for sentence in split_sentences(transcript):
            lowered = sentence.lower()
            categories = [category for pattern, category in _CATEGORY_PATTERNS if re.search(pattern, lowered)]
            if not categories:
                continue
            primary = categories[0]
            if primary in seen:
                continue
            seen.add(primary)
            negations = detect_negations(sentence)
            observations.append(
                ClinicalObservation(
                    observation=sentence,
                    category=primary,
                    source="transcript",
                    confidence=None,
                    evidence=[sentence],
                    uncertainty_note=(
                        "Reported by the patient. Negation present in this span: "
                        + ", ".join(negations)
                        if negations
                        else "Patient-reported statement; not independently verified."
                    ),
                )
            )

        for symptom in _explicit_symptom_phrases(transcript):
            key = f"symptom:{symptom}"
            if key in seen:
                continue
            seen.add(key)
            observations.append(
                ClinicalObservation(
                    observation=f"Patient explicitly mentions: {symptom}.",
                    category=f"symptom:{symptom}",
                    source="transcript",
                    evidence=[symptom],
                    uncertainty_note="Surface-level extraction from the transcript; no inference added.",
                )
            )
        return observations[:20]

    # ------------------------------------------------------------------ main
    async def analyze(
        self,
        data: bytes,
        *,
        filename: str = "clip.wav",
        language: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> SpeechAnalysisResponse:
        started = time.perf_counter()
        rid = request_id or uuid.uuid4().hex[:12]
        settings = get_settings()
        warnings: List[str] = []
        extension = audio_utils.guess_extension(filename, data)

        # ---------------------------------------------------- decode + measure
        try:
            audio = audio_utils.load_audio(data, extension)
        except AppError as exc:
            if exc.code == ErrorCode.UNSUPPORTED_FORMAT and audio_utils.NUMPY_AVAILABLE:
                raise
            raise

        features_raw = audio_utils.compute_acoustic_features(
            audio["array"], audio_utils.TARGET_SAMPLE_RATE
        )
        speech_features = [
            SpeechFeature(
                name=str(f["name"]),
                value=f.get("value"),
                unit=str(f.get("unit", "")),
                score=f.get("score"),
                measured=bool(f.get("measured", True)),
                category=str(f.get("category", "acoustic")),
                notes=str(f.get("notes", "")),
            )
            for f in features_raw
        ]

        # ----------------------------------------------------------- transcribe
        transcript = ""
        segments: List[TranscriptSegment] = []
        asr_model, backend_name, asr_status = self._load_asr()
        asr_confidence: Optional[float] = None

        if asr_model is not None:
            try:
                with secure_temp_file(suffix=extension or ".wav", max_age_seconds=3600) as tmp:
                    tmp.write_bytes(data)
                    transcript, segments, asr_confidence = await self._transcribe(
                        asr_model, tmp, language
                    )
            except Exception as exc:
                logger.warning("asr_failed", extra={"error": str(exc)[:300]})
                warnings.append(f"Speech recognition failed: {str(exc)[:200]}")
                asr_status = "error"
        elif settings.MOCK_MODE:
            asr_status = "simulated"
            warnings.append(
                "MOCK_MODE=true: no speech recognition model was called. No transcript is "
                "reported and no symptoms are inferred from audio."
            )
        else:
            warnings.append(
                "No local speech recognition model is available. Install 'faster-whisper' and "
                "set WHISPER_MODEL_PATH, or install one of the whisper.cpp bindings."
            )

        observations = self._observations_from_transcript(transcript)
        if not transcript:
            observations.append(
                ClinicalObservation(
                    observation=(
                        "No transcript is available for this clip; no symptoms were extracted "
                        "from speech."
                        if asr_status != "error"
                        else "Speech recognition failed; no transcript is available and no "
                        "symptoms were extracted."
                    ),
                    category="availability",
                    source="unavailable",
                    confidence=0.0,
                    uncertainty_note=(
                        "The only evidence from this modality is the measured acoustic "
                        "features listed in speech_features."
                    ),
                )
            )

        # --------------------------------------------------------- LLM structuring
        llm_used = False
        if transcript and not settings.MOCK_MODE:
            structured = await self._structure_with_llm(transcript, observations)
            if structured:
                observations = structured
                llm_used = True

        # --------------------------------------------------------------- meta
        missing: List[str] = []
        if not transcript:
            missing.append("Verbatim transcript (configure a local Whisper model).")
        if not audio.get("duration_seconds"):
            missing.append("Audio duration metadata.")

        signal_quality = _signal_quality(speech_features)
        confidence = 0.0
        drivers: List[str] = []
        if transcript:
            confidence = 0.75
            if asr_confidence is not None:
                confidence = round(min(0.55 + asr_confidence * 0.35, 0.95), 4)
            drivers.append(f"ASR backend: {backend_name}.")
        else:
            confidence = 0.25
            drivers.append("No transcript was produced, so no clinical content can be assessed.")
        if signal_quality == "poor":
            confidence = max(0.0, confidence - 0.15)
            drivers.append("Audio signal quality is poor; acoustic features are unreliable.")

        uncertainty = Uncertainty(
            overall=round(1.0 - confidence, 4),
            confidence=round(confidence, 4),
            epistemic=round(0.5 if not transcript else 0.2, 4),
            aleatoric=round(0.3, 4),
            drivers=dedupe_preserve_order(drivers),
            missing_information=missing,
            notes=(
                "Confidence reflects ASR availability and measured signal quality, not a "
                "calibrated clinical accuracy estimate."
            ),
        )

        simulated = asr_status in {"simulated", "unavailable", "error"}
        provenance = Provenance(
            mode="simulated" if simulated else "real",
            label="DEMO / SIMULATED" if simulated else "REAL LOCAL INFERENCE",
            computed_by=backend_name or "local_signal_processing",
            simulated=simulated,
            notes=(
                "speech_features are genuinely measured from the submitted audio. "
                + (
                    "No speech recognition model produced a transcript."
                    if simulated
                    else "Transcript produced by the configured local ASR model."
                )
            ),
        )

        return SpeechAnalysisResponse(
            success=True,
            transcript=transcript,
            segments=segments,
            clinical_observations=dedupe_observations(observations),
            speech_features=speech_features,
            uncertainty=uncertainty,
            model=model_manager.speech_info(asr_status, backend_name),
            limitations=self._limitations(),
            missing_information=missing,
            metadata=SpeechMetadata(
                filename=filename[:200],
                content_type=sniff_content_type(data) or "audio/wav",
                size_bytes=len(data),
                format=extension.lstrip(".").lower(),
                duration_seconds=audio.get("duration_seconds"),
                sample_rate_hz=audio.get("sample_rate_hz"),
                channels=audio.get("channels"),
                resampled_to_hz=audio.get("resampled_to_hz"),
                rms_dbfs=_feature_value(speech_features, "rms_level"),
                peak_dbfs=_feature_value(speech_features, "peak_level"),
                silence_ratio=_feature_value(speech_features, "silence_ratio"),
                clipped_ratio=_feature_value(speech_features, "clipped_ratio"),
            ),
            provenance=provenance,
            request_id=rid,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            warnings=warnings,
        )

    async def _structure_with_llm(
        self, transcript: str, fallback: List[ClinicalObservation]
    ) -> List[ClinicalObservation]:
        """Ask the local LLM to structure the transcript; verify its output.

        The model may only *select and label* spans that exist in the transcript.
        Anything not verifiable in the source text is discarded.
        """
        prompt = (
            "TASK: extract clinical statements from the patient transcript below.\n"
            "RULES:\n"
            "- Only use words present in the transcript. Never add a symptom that is absent.\n"
            "- For each statement, return the exact verbatim span from the transcript as 'evidence'.\n"
            "- Classify each statement into one of: symptom, timeline, negation, history, other.\n"
            "- Do not give a diagnosis or interpretation.\n"
            "TRANSCRIPT:\n" + transcript + "\n\n"
            'Return JSON: {"observations":[{"observation":"...","category":"...","evidence":"..."}]}'
        )
        result = await llm_service.complete_json(prompt, temperature=0.0, num_predict=1024)
        data = result.get("data")
        if not isinstance(data, dict):
            return fallback
        raw = data.get("observations")
        if not isinstance(raw, list):
            return fallback

        lowered_transcript = transcript.lower()
        verified: List[ClinicalObservation] = []
        for item in raw[:20]:
            if not isinstance(item, dict):
                continue
            statement = str(item.get("observation") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            if not statement:
                continue
            # Guard against hallucinated content: the evidence span must be real.
            if evidence and evidence.lower() not in lowered_transcript:
                logger.info("llm_observation_rejected_unverifiable_span")
                continue
            verified.append(
                ClinicalObservation(
                    observation=statement[:1000],
                    category=str(item.get("category") or "other")[:80],
                    source="model_structured",
                    evidence=[evidence] if evidence else [],
                    uncertainty_note=(
                        "Structured by the configured local LLM from a transcript span that was "
                        "verified to exist in the source text. Requires clinician verification."
                    ),
                )
            )
        return verified or fallback


# ------------------------------------------------------------------- helpers
def _faster_whisper_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:
        return False


def _load_faster_whisper(model_path: Any, settings: Any) -> Any:
    from faster_whisper import WhisperModel  # type: ignore

    device = settings.WHISPER_DEVICE
    if device == "auto":
        try:
            import torch  # type: ignore

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
    return WhisperModel(
        str(model_path),
        device=device,
        compute_type=settings.WHISPER_COMPUTE_TYPE if device == "cpu" else "float16",
    )


def _explicit_symptom_phrases(transcript: str) -> List[str]:
    from app.utils.validation import SYMPTOM_LEXICON

    lowered = transcript.lower()
    found: List[str] = []
    for symptom, patterns in SYMPTOM_LEXICON.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                found.append(symptom.replace("_", " "))
                break
    return found


def dedupe_observations(items: List[ClinicalObservation]) -> List[ClinicalObservation]:
    seen: set[str] = set()
    out: List[ClinicalObservation] = []
    for item in items:
        key = item.observation.strip().lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _feature_value(features: List[SpeechFeature], name: str) -> Optional[float]:
    for feature in features:
        if feature.name == name and isinstance(feature.value, (int, float)):
            return float(feature.value)
    return None


def _signal_quality(features: List[SpeechFeature]) -> str:
    """Coarse signal-quality verdict from measured levels (a flag, not a finding)."""
    rms = _feature_value(features, "rms_level")
    clipped = _feature_value(features, "clipped_ratio")
    silence = _feature_value(features, "silence_ratio")
    if rms is None:
        return "unknown"
    if rms < -45 or (clipped or 0) > 0.25 or (silence or 0) > 0.7:
        return "poor"
    if rms > -12:
        return "loud"
    return "acceptable"


speech_service = SpeechService()
