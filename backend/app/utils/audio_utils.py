"""Audio decoding, resampling and acoustic measurement.

Uses the standard library ``wave`` module plus NumPy so that basic WAV/PCM
analysis needs no extra dependencies. Optional backends (``soundfile``,
``librosa``, ``ffmpeg``) are used when installed for compressed formats.
"""

from __future__ import annotations

import contextlib
import io
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.errors import AppError, ErrorCode
from app.core.security import guess_extension, sniff_content_type

try:  # pragma: no cover - import guard
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None  # type: ignore[assignment]

try:  # pragma: no cover - import guard
    import soundfile as _sf
except Exception:  # pragma: no cover
    _sf = None  # type: ignore[assignment]

try:  # pragma: no cover - import guard
    import librosa as _librosa
except Exception:  # pragma: no cover
    _librosa = None  # type: ignore[assignment]

NUMPY_AVAILABLE = _np is not None
SOUNDFILE_AVAILABLE = _sf is not None
LIBROSA_AVAILABLE = _librosa is not None

TARGET_SAMPLE_RATE = 16000


def dependency_status() -> Dict[str, bool]:
    return {
        "numpy": NUMPY_AVAILABLE,
        "soundfile": SOUNDFILE_AVAILABLE,
        "librosa": LIBROSA_AVAILABLE,
    }


def ffmpeg_available() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _decode_wav(data: bytes) -> Tuple[Any, int]:
    if _np is None:
        raise AppError(
            ErrorCode.INTERNAL_ERROR, "Audio analysis requires NumPy.", status_code=500
        )
    try:
        with contextlib.closing(wave_open(io.BytesIO(data))) as wav:
            channels = wav.getnchannels() or 1
            width = wav.getsampwidth() or 2
            rate = wav.getframerate() or TARGET_SAMPLE_RATE
            frames = wav.readframes(wav.getnframes())
    except Exception as exc:
        raise AppError(
            ErrorCode.UNSUPPORTED_FORMAT,
            f"WAV audio could not be decoded: {exc}",
            status_code=415,
        ) from exc

    dtype_map = {1: _np.uint8, 2: _np.int16, 4: _np.int32}
    dtype = dtype_map.get(width, _np.int16)
    array = _np.frombuffer(frames, dtype=dtype).astype(_np.float64)
    if width == 1:
        array = (array - 128.0) / 128.0
    else:
        info = _np.iinfo(dtype)
        array = array / float(info.max)
    if channels > 1:
        array = array.reshape(-1, channels).mean(axis=1)
    return array, int(rate)


def _decode_with_soundfile(data: bytes) -> Optional[Tuple[Any, int]]:
    if _sf is None:
        return None
    try:
        array, rate = _sf.read(io.BytesIO(data), dtype="float64", always_2d=False)
        array = _np.asarray(array, dtype=_np.float64)
        if array.ndim > 1:
            array = array.mean(axis=1)
        return array, int(rate)
    except Exception:
        return None


def _decode_with_librosa(data: bytes) -> Optional[Tuple[Any, int]]:
    if _librosa is None or _np is None:
        return None
    try:
        array, rate = _librosa.load(io.BytesIO(data), sr=None, mono=True)
        return _np.asarray(array, dtype=_np.float64), int(rate)
    except Exception:
        return None


def _decode_with_ffmpeg(data: bytes, extension: str) -> Optional[Tuple[Any, int]]:
    if not ffmpeg_available() or _np is None:
        return None
    tmp = None
    try:
        handle, path = tempfile.mkstemp(suffix=extension or ".bin")
        tmp = Path(path)
        with open(handle, "wb") as fh:  # type: ignore[arg-type]
            fh.write(data)
        out = tmp.with_suffix(".wav")
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(tmp), "-ac", "1", "-ar", str(TARGET_SAMPLE_RATE), str(out),
            ],
            check=True,
            timeout=90,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return _decode_wav(out.read_bytes())
    except Exception:
        return None
    finally:
        if tmp and tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()
            with_ = tmp.with_suffix(".wav")
            if with_.exists():
                with contextlib.suppress(OSError):
                    with_.unlink()


def wave_open(stream: Any):  # pragma: no cover - thin wrapper for contextlib
    import wave

    return wave.open(stream, "rb")


def load_audio(data: bytes, extension: str = "") -> Dict[str, Any]:
    """Decode audio to a mono float array, resampled to 16 kHz.

    Backend order: soundfile -> librosa -> ffmpeg -> builtin WAV reader.
    Raises :class:`AppError` when the audio cannot be decoded at all.
    """
    if not data:
        raise AppError(ErrorCode.INVALID_FILE, "The uploaded audio file is empty.", status_code=400)

    decoded: Optional[Tuple[Any, int]] = None
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        decoded = _decode_wav(data)  # raises on corruption
    if decoded is None:
        decoded = _decode_with_soundfile(data)
    if decoded is None:
        decoded = _decode_with_librosa(data)
    if decoded is None:
        decoded = _decode_with_ffmpeg(data, extension)
    if decoded is None and data[:4] == b"RIFF":
        decoded = _decode_wav(data)
    if decoded is None:
        raise AppError(
            ErrorCode.UNSUPPORTED_FORMAT,
            "Audio could not be decoded. Install 'soundfile' or 'ffmpeg' for compressed formats.",
            status_code=415,
        )

    array, source_rate = decoded
    resampled_rate: Optional[int] = None
    if source_rate and source_rate != TARGET_SAMPLE_RATE:
        array = resample(array, source_rate, TARGET_SAMPLE_RATE)
        resampled_rate = TARGET_SAMPLE_RATE

    duration = float(len(array)) / float(TARGET_SAMPLE_RATE) if TARGET_SAMPLE_RATE else 0.0
    return {
        "array": array,
        "sample_rate_hz": source_rate,
        "effective_sample_rate_hz": TARGET_SAMPLE_RATE,
        "resampled_to_hz": resampled_rate,
        "channels": 1,
        "duration_seconds": round(duration, 3),
    }


def resample(array: Any, source_rate: int, target_rate: int) -> Any:
    """Linear-interpolation resampling (sufficient for feature measurement)."""
    if _np is None or array is None or source_rate == target_rate or len(array) == 0:
        return array
    duration = len(array) / float(source_rate)
    target_length = max(int(round(duration * target_rate)), 1)
    source_positions = _np.linspace(0.0, len(array) - 1, num=len(array))
    target_positions = _np.linspace(0.0, len(array) - 1, num=target_length)
    return _np.interp(target_positions, source_positions, array)


def compute_acoustic_features(array: Any, sample_rate: int = TARGET_SAMPLE_RATE) -> List[Dict[str, Any]]:
    """Deterministic, interpretable acoustic measurements.

    Every value here is genuinely computed from the submitted audio. None of it
    is a diagnosis: speech-rate estimates are reported as estimates with their
    measurement assumptions spelled out.
    """
    if _np is None or array is None or len(array) == 0:
        return []

    arr = _np.asarray(array, dtype=_np.float64)
    peak = float(_np.max(_np.abs(arr))) if arr.size else 0.0
    rms = float(_np.sqrt(_np.mean(arr**2))) if arr.size else 0.0

    eps = 1e-12
    rms_dbfs = 20.0 * math.log10(max(rms, eps))
    peak_dbfs = 20.0 * math.log10(max(peak, eps))

    # Silence / clipping ratios.
    frame = max(int(sample_rate * 0.02), 1)
    usable = (len(arr) // frame) * frame
    silence_ratio = 0.0
    clipped_ratio = 0.0
    if usable:
        frames = arr[:usable].reshape(-1, frame)
        frame_rms = _np.sqrt(_np.mean(frames**2, axis=1))
        silence_ratio = float(_np.mean(frame_rms < 0.01))
        clipped_ratio = float(_np.mean(_np.max(_np.abs(frames), axis=1) > 0.99))

    # Zero-crossing rate.
    zcr = float(_np.mean(_np.abs(_np.diff(_np.signbit(arr)).astype(_np.float64)))) if len(arr) > 1 else 0.0

    # Spectral centroid via a NumPy FFT (vocant brightness proxy).
    centroid_hz: Optional[float] = None
    if len(arr) >= 512:
        windowed = arr[: len(arr) // 512 * 512].reshape(-1, 512)
        window = _np.hanning(512)
        spectrum = _np.abs(_np.fft.rfft(windowed * window, axis=1)).mean(axis=0)
        freqs = _np.fft.rfftfreq(512, d=1.0 / sample_rate)
        total = float(spectrum.sum())
        if total > eps:
            centroid_hz = float((spectrum * freqs).sum() / total)

    # Energy-based speech/silence segmentation -> measured speech rate.
    speech_segments, voiced_rate = _energy_segmentation(arr, sample_rate)

    features: List[Dict[str, Any]] = [
        {
            "name": "duration",
            "value": round(len(arr) / float(sample_rate), 3),
            "unit": "s",
            "measured": True,
            "category": "temporal",
            "notes": "Total audio duration after resampling.",
        },
        {
            "name": "rms_level",
            "value": round(rms_dbfs, 2),
            "unit": "dBFS",
            "score": round(min(max((rms_dbfs + 60.0) / 60.0, 0.0), 1.0), 4),
            "measured": True,
            "category": "loudness",
            "notes": "Root-mean-square level relative to full scale.",
        },
        {
            "name": "peak_level",
            "value": round(peak_dbfs, 2),
            "unit": "dBFS",
            "measured": True,
            "category": "loudness",
            "notes": "Peak sample level; near 0 dBFS indicates clipping.",
        },
        {
            "name": "silence_ratio",
            "value": round(silence_ratio, 4),
            "score": round(silence_ratio, 4),
            "measured": True,
            "category": "temporal",
            "notes": "Fraction of 20 ms frames below the -40 dBFS speech threshold.",
        },
        {
            "name": "clipped_ratio",
            "value": round(clipped_ratio, 4),
            "score": round(clipped_ratio, 4),
            "measured": True,
            "category": "signal_quality",
            "notes": "Fraction of frames containing samples at full scale.",
        },
        {
            "name": "zero_crossing_rate",
            "value": round(zcr, 4),
            "score": round(zcr, 4),
            "measured": True,
            "category": "acoustic",
            "notes": "Sign-change rate; higher values indicate more high-frequency content.",
        },
    ]

    if centroid_hz is not None:
        features.append(
            {
                "name": "spectral_centroid",
                "value": round(centroid_hz, 1),
                "unit": "Hz",
                "score": round(min(centroid_hz / 4000.0, 1.0), 4),
                "measured": True,
                "category": "acoustic",
                "notes": "Mean frequency weighted by spectral magnitude (voiced-brightness proxy).",
            }
        )

    if speech_segments and voiced_rate is not None:
        features.append(
            {
                "name": "measured_segment_rate",
                "value": round(voiced_rate, 1),
                "unit": "segments/min",
                "score": round(min(voiced_rate / 40.0, 1.0), 4),
                "measured": True,
                "category": "prosody",
                "notes": "Rate of contiguous energy segments (breath/syllable-group proxy). "
                "This is a signal-processing estimate, not a respiratory-rate measurement.",
            }
        )
        features.append(
            {
                "name": "energy_segment_count",
                "value": len(speech_segments),
                "unit": "count",
                "measured": True,
                "category": "prosody",
                "notes": "Number of contiguous above-threshold energy regions.",
            }
        )
    return features


def _energy_segmentation(arr: Any, sample_rate: int) -> Tuple[List[Tuple[float, float]], Optional[float]]:
    """Split the signal into above-threshold energy regions."""
    if _np is None or len(arr) == 0:
        return [], None
    hop = max(int(sample_rate * 0.02), 1)
    usable = (len(arr) // hop) * hop
    if usable == 0:
        return [], None
    frames = arr[:usable].reshape(-1, hop)
    energy = _np.sqrt(_np.mean(frames**2, axis=1))
    if energy.size == 0:
        return [], None
    threshold = max(float(energy.max()) * 0.12, 1e-4)
    active = energy > threshold
    segments: List[Tuple[float, float]] = []
    start: Optional[int] = None
    min_frames = 3  # >=60 ms to avoid counting clicks
    for idx, flag in enumerate(active):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            if idx - start >= min_frames:
                segments.append((start * hop / sample_rate, idx * hop / sample_rate))
            start = None
    if start is not None and len(active) - start >= min_frames:
        segments.append((start * hop / sample_rate, len(active) * hop / sample_rate))

    total_speech = sum(end - start for start, end in segments)
    if total_speech <= 0:
        return segments, None
    rate = (len(segments) / total_speech) * 60.0
    return segments, rate


def segments_to_windows(segments: List[Tuple[float, float]], limit: int = 32) -> List[Tuple[float, float]]:
    """Merge adjacent segments into analysis windows, capped at ``limit``."""
    if not segments:
        return []
    windows: List[List[float]] = []
    for start, end in segments:
        if windows and start - windows[-1][1] < 0.25:
            windows[-1][1] = end
        else:
            windows.append([start, end])
    return [(round(a, 3), round(b, 3)) for a, b in windows[:limit]]
