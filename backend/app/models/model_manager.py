"""Central model registry and availability reporting.

The manager owns *availability* and *identity* of every model the system can use.
It deliberately does not preload heavyweight artefacts: loading is lazy, cached,
and always optional. Nothing in this module fabricates a model that is not
actually installed.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional, TypeVar

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.common import ModelInfo

logger = get_logger(__name__)

T = TypeVar("T")

#: Cache lifetime for a negative availability probe, so /api/health stays fast.
_PROBE_TTL_SECONDS = 15.0


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl


class ModelManager:
    """Lazy, thread-safe registry of local models and their status."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._singletons: Dict[str, Any] = {}
        self._probe_cache: Dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------ probes
    def probe(self, key: str, probe: Callable[[], Any], ttl: float = _PROBE_TTL_SECONDS) -> Any:
        """Run an availability probe with a short cache to avoid repeated I/O."""
        now = time.monotonic()
        with self._lock:
            entry = self._probe_cache.get(key)
            if entry and entry.expires_at > now:
                return entry.value
        value = probe()
        with self._lock:
            self._probe_cache[key] = _CacheEntry(value, ttl)
        return value

    def invalidate(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._probe_cache.clear()
            else:
                self._probe_cache.pop(key, None)

    # -------------------------------------------------------------- lazy loads
    def singleton(self, key: str, factory: Callable[[], T], *, probe: Optional[Callable[[], bool]] = None) -> Optional[T]:
        """Return a cached singleton, or ``None`` when it cannot be created.

        A failed construction is not cached, so installing a model and retrying
        works without restarting the process.
        """
        with self._lock:
            if key in self._singletons:
                return self._singletons[key]
        if probe is not None and not probe():
            return None
        try:
            instance = factory()
        except Exception as exc:  # pragma: no cover - depends on optional deps
            logger.warning("model_load_failed", extra={"model_key": key, "error": str(exc)[:300]})
            return None
        with self._lock:
            self._singletons[key] = instance
            self._probe_cache.pop(key, None)
        return instance

    def loaded(self, key: str) -> bool:
        with self._lock:
            return key in self._singletons

    def clear(self) -> None:
        with self._lock:
            self._singletons.clear()
            self._probe_cache.clear()

    # ------------------------------------------------------------ model info
    def llm_info(self, status: str = "unknown", name: Optional[str] = None) -> ModelInfo:
        settings = get_settings()
        model_name = name or settings.OLLAMA_LLM_MODEL
        return ModelInfo(
            name=model_name or "unconfigured",
            role="clinical_reasoning",
            status=status,
            source="ollama",
            parameters={"base_url": settings.OLLAMA_BASE_URL, "mock_mode": settings.MOCK_MODE},
        )

    def vision_info(self, status: str = "unavailable") -> ModelInfo:
        settings = get_settings()
        return ModelInfo(
            name=settings.OLLAMA_VISION_MODEL or "unconfigured",
            role="vision_language",
            status=status,
            source="ollama",
            parameters={"base_url": settings.OLLAMA_BASE_URL},
        )

    def embedding_info(self, status: str = "unknown", dimension: int = 0) -> ModelInfo:
        settings = get_settings()
        if settings.EMBEDDING_PROVIDER == "ollama":
            return ModelInfo(
                name=settings.embedding_model or "unconfigured",
                role="text_embedding",
                status=status,
                source="ollama",
                parameters={"dimension": dimension or settings.EMBEDDING_DIM},
            )
        if settings.EMBEDDING_PROVIDER == "sentence-transformers":
            return ModelInfo(
                name=settings.SENTENCE_TRANSFORMER_MODEL,
                role="text_embedding",
                status=status,
                source="sentence_transformers",
                parameters={"dimension": dimension or settings.EMBEDDING_DIM},
            )
        return ModelInfo(
            name="hashing-fallback",
            role="text_embedding",
            status=status,
            source="builtin",
            parameters={"dimension": dimension, "note": "Deterministic lexical fallback; no semantics."},
        )

    def speech_info(self, status: str = "unavailable", name: str = "") -> ModelInfo:
        settings = get_settings()
        return ModelInfo(
            name=name or (settings.WHISPER_MODEL_PATH or "unconfigured"),
            role="speech_recognition",
            status=status,
            source="local_whisper",
            parameters={"device": settings.WHISPER_DEVICE, "compute_type": settings.WHISPER_COMPUTE_TYPE},
        )

    def fusion_info(self, status: str = "integration_layer") -> ModelInfo:
        return ModelInfo(
            name="MedExplainFusionService",
            role="multimodal_fusion",
            status=status,
            source="application_code",
            parameters={
                "type": "structured_representation_integration",
                "is_trained_neural_fusion_model": False,
                "note": "Integration/prototype fusion layer over per-modality representations; "
                "not a newly trained cross-attention network.",
            },
        )


model_manager = ModelManager()
