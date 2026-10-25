"""Text embedding service with pluggable local providers.

Providers (``EMBEDDING_PROVIDER`` in ``.env``)
----------------------------------------------
``ollama``
    Uses a local Ollama embedding model. No PyTorch required. Preferred default
    for a local-first deployment.
``sentence-transformers``
    Uses a local sentence-transformers checkpoint (requires torch).
``hashing``
    Dependency-free deterministic lexical fallback. **Not semantic** -- it
    exists so the ingestion/search plumbing is testable, and every response
    using it is labelled accordingly.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import threading
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.models.model_manager import model_manager
from app.schemas.common import ModelInfo
from app.services.llm_service import llm_service

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Number of buckets for the deterministic hashing fallback.
HASH_BUCKETS = 1024


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class EmbeddingService:
    """Encodes text to vectors using whichever local provider is configured."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dimension: Optional[int] = None
        self._st_model: Any = None
        self._st_attempted = False
        self._ollama_attempted = False
        self._ollama_failed = False

    # ------------------------------------------------------------- properties
    @property
    def provider(self) -> str:
        return get_settings().EMBEDDING_PROVIDER.lower()

    @property
    def dimension(self) -> int:
        if self._dimension is not None:
            return self._dimension
        return get_settings().EMBEDDING_DIM

    # ------------------------------------------------------------- providers
    def _load_sentence_transformer(self) -> Any:
        settings = get_settings()
        with self._lock:
            if self._st_model is not None:
                return self._st_model
            if self._st_attempted:
                return None
            self._st_attempted = True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL, device="cpu")
            with self._lock:
                self._st_model = model
                self._dimension = int(model.get_sentence_embedding_dimension())
            logger.info("sentence_transformers_loaded", extra={"model": settings.SENTENCE_TRANSFORMER_MODEL})
            return model
        except Exception as exc:
            logger.warning("sentence_transformers_unavailable", extra={"error": str(exc)[:300]})
            return None

    async def _embed_ollama(self, texts: Sequence[str]) -> Optional[List[List[float]]]:
        if self._ollama_failed:
            return None
        try:
            vectors = await llm_service.client.embed(list(texts))
        except AppError as exc:
            self._ollama_failed = True
            logger.warning("ollama_embedding_unavailable", extra={"error": exc.message})
            return None
        if vectors:
            with self._lock:
                self._dimension = len(vectors[0])
        return vectors

    def _embed_sentence_transformers(self, texts: Sequence[str]) -> Optional[List[List[float]]]:
        model = self._load_sentence_transformer()
        if model is None:
            return None
        try:
            matrix = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
            vectors = [[float(x) for x in row] for row in matrix]
            with self._lock:
                self._dimension = len(vectors[0]) if vectors else self._dimension
            return vectors
        except Exception as exc:
            logger.warning("sentence_transformers_encode_failed", extra={"error": str(exc)[:300]})
            return None

    def _embed_hashing(self, texts: Sequence[str]) -> List[List[float]]:
        """Deterministic bag-of-tokens hashing with sublinear term weighting.

        Lexical only: it captures exact/shared token overlap, not paraphrase
        similarity. Reported as such everywhere it is used.
        """
        vectors: List[List[float]] = []
        for text in texts:
            vector = np.zeros(HASH_BUCKETS, dtype=np.float64)
            tokens = tokenize(text)
            if tokens:
                for token in tokens:
                    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                    bucket = int.from_bytes(digest[:4], "big") % HASH_BUCKETS
                    sign = 1.0 if digest[4] & 1 else -1.0
                    vector[bucket] += sign
                vector = np.sign(vector) * (1.0 + np.log(np.abs(vector) + 1.0))
            norm = float(np.linalg.norm(vector))
            vectors.append((vector / norm).tolist() if norm > 0 else vector.tolist())
        with self._lock:
            self._dimension = HASH_BUCKETS
        return vectors

    # ----------------------------------------------------------------- public
    async def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Encode texts, falling back through the configured providers."""
        items = [t if (t or "").strip() else " " for t in texts]
        if not items:
            return []

        provider = self.provider
        if provider == "sentence-transformers":
            vectors = await asyncio.to_thread(self._embed_sentence_transformers, items)
            if vectors:
                return vectors
            logger.warning("embedding_provider_fallback", extra={"from": provider, "to": "ollama"})
        elif provider == "ollama":
            vectors = await self._embed_ollama(items)
            if vectors:
                return vectors
            logger.warning("embedding_provider_fallback", extra={"from": provider, "to": "hashing"})
        return self._embed_hashing(items)

    async def embed_one(self, text: str) -> List[float]:
        vectors = await self.embed([text])
        return vectors[0] if vectors else []

    def embed_sync(self, texts: Sequence[str]) -> List[List[float]]:
        """Synchronous variant for CLI scripts (hashing/provider fallback)."""
        if self.provider == "hashing":
            return self._embed_hashing(list(texts))
        vectors = self._embed_sentence_transformers(list(texts))
        if vectors:
            return vectors
        return self._embed_hashing(list(texts))

    # ------------------------------------------------------------- reporting
    def info(self) -> ModelInfo:
        provider = self.provider
        if provider == "sentence-transformers" and self._st_model is not None:
            return model_manager.embedding_info("loaded", self.dimension)
        if provider == "ollama":
            settings = get_settings()
            status = "configured" if settings.embedding_model else "unconfigured"
            return ModelInfo(
                name=settings.embedding_model or "unconfigured",
                role="text_embedding",
                status=status,
                source="ollama",
                parameters={"dimension": self.dimension, "base_url": settings.OLLAMA_BASE_URL},
            )
        if provider == "hashing":
            return ModelInfo(
                name="hashing-fallback",
                role="text_embedding",
                status="fallback",
                source="builtin",
                parameters={
                    "dimension": HASH_BUCKETS,
                    "note": "Deterministic lexical hashing. Matches exact/shared tokens only; "
                    "it is not a semantic embedding model.",
                },
            )
        status = "loaded" if self._st_model is not None else "unavailable"
        return model_manager.embedding_info(status, self.dimension)

    def is_semantic(self) -> bool:
        return self.provider in {"ollama", "sentence-transformers"} and self._st_model is not None or self.provider == "ollama"

    def available(self) -> bool:
        """True when a real encoder exists (or could be provisioned)."""
        if self.provider == "hashing":
            return False
        if self.provider == "sentence-transformers":
            return self._st_model is not None
        return bool(get_settings().embedding_model)


embedding_service = EmbeddingService()


def l2_normalize(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    """Return an L2-normalized float32 matrix, safe for zero vectors."""
    if not vectors:
        return np.zeros((0, 0), dtype=np.float32)
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def require_embeddings(vectors: List[List[float]], *, allow_fallback: bool = True) -> List[List[float]]:
    if not vectors:
        raise AppError(
            ErrorCode.EMBEDDING_MODEL_UNAVAILABLE,
            "No embedding vectors were produced.",
            status_code=503,
        )
    if not allow_fallback:
        settings = get_settings()
        if settings.EMBEDDING_PROVIDER == "hashing":
            raise AppError(
                ErrorCode.EMBEDDING_MODEL_UNAVAILABLE,
                "No real embedding model is configured. Set OLLAMA_EMBEDDING_MODEL or "
                "EMBEDDING_PROVIDER=sentence-transformers.",
                status_code=503,
            )
    return vectors


def metadata_vector_summary(vectors: List[List[float]], limit: int = 6) -> Dict[str, Any]:
    """Small diagnostic summary, useful in /api/health and tests."""
    if not vectors:
        return {"count": 0}
    summary: Dict[str, Any] = {
        "count": len(vectors),
        "dimension": len(vectors[0]),
        "norms": [round(float(math.sqrt(sum(v * v for v in vec))), 4) for vec in vectors[:limit]],
    }
    return summary
