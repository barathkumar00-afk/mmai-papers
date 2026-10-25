"""FAISS-backed evidence retrieval with a JSON metadata sidecar.

Layout on disk::

    data/indexes/medical.index      # faiss binary index
    data/indexes/metadata.json      # parallel list of chunk records

The sidecar is the source of truth for provenance: every returned chunk carries
its real document id, title and source. If the index is missing or empty, the
service reports ``Knowledge base not initialized`` rather than inventing hits.
"""

from __future__ import annotations

import json
import math
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.retrieval import RetrievedEvidence
from app.services.embedding_service import embedding_service, l2_normalize

logger = get_logger(__name__)

try:  # pragma: no cover - import guard
    import faiss as _faiss

    FAISS_AVAILABLE = True
except Exception:  # pragma: no cover
    _faiss = None  # type: ignore[assignment]
    FAISS_AVAILABLE = False


def faiss_available() -> bool:
    return FAISS_AVAILABLE


def chunk_text(
    text: str,
    *,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
) -> List[str]:
    """Split text on paragraph/sentence boundaries with a character overlap."""
    settings = get_settings()
    size = chunk_size or settings.CHUNK_SIZE
    window = overlap if overlap is not None else settings.CHUNK_OVERLAP
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    # Prefer natural boundaries, then fall back to a hard split.
    sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    chunks: List[str] = []
    buffer = ""
    for sentence in sentences:
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= size:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        if len(sentence) > size:
            # Very long sentence: hard-split with overlap.
            step = max(size - window, 1)
            for start in range(0, len(sentence), step):
                piece = sentence[start : start + size]
                if piece.strip():
                    chunks.append(piece.strip())
                if start + size >= len(sentence):
                    break
            buffer = ""
        else:
            buffer = sentence
    if buffer.strip():
        chunks.append(buffer.strip())

    if window > 0 and len(chunks) > 1:
        merged: List[str] = []
        for index, chunk in enumerate(chunks):
            if index == 0:
                merged.append(chunk)
                continue
            tail = chunks[index - 1][-window:]
            merged.append(f"{tail}\n{chunk}".strip())
        chunks = merged
    return chunks


class RetrievalService:
    """Owns the FAISS index lifecycle and similarity search."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._index: Any = None
        self._records: List[Dict[str, Any]] = []
        self._vectors: List[List[float]] = []
        self._dimension: int = 0
        self._index_type: str = ""
        self._loaded_from_disk = False

    # ------------------------------------------------------------- properties
    @property
    def index_path(self) -> Path:
        return get_settings().faiss_index_path

    @property
    def metadata_path(self) -> Path:
        return get_settings().faiss_metadata_path

    @property
    def similarity_metric(self) -> str:
        return "cosine"

    @property
    def initialized(self) -> bool:
        return self._index is not None and bool(self._records)

    @property
    def total_documents(self) -> int:
        return len({r.get("document_id") for r in self._records})

    @property
    def total_chunks(self) -> int:
        return len(self._records)

    @property
    def dimension(self) -> int:
        return self._dimension

    # ------------------------------------------------------------ persistence
    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self.initialized,
                "index_path": str(self.index_path),
                "metadata_path": str(self.metadata_path),
                "index_exists_on_disk": self.index_path.exists(),
                "metadata_exists_on_disk": self.metadata_path.exists(),
                "total_documents": self.total_documents,
                "total_chunks": self.total_chunks,
                "dimension": self._dimension,
                "index_type": self._index_type,
                "similarity_metric": self.similarity_metric,
                "faiss_available": FAISS_AVAILABLE,
                "loaded_from_disk": self._loaded_from_disk,
            }

    def load(self, *, force: bool = False) -> bool:
        """Load the on-disk index if present. Never raises."""
        if not FAISS_AVAILABLE:
            logger.info("faiss_unavailable", extra={"note": "retrieval will report unavailable"})
            return False
        with self._lock:
            if self._index is not None and not force:
                return True
            if not self.index_path.exists() or not self.metadata_path.exists():
                self._index = None
                self._records = []
                self._loaded_from_disk = False
                return False
            try:
                index = _faiss.read_index(str(self.index_path))
                payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error("faiss_load_failed", extra={"error": str(exc)[:400]})
                self._index = None
                self._records = []
                self._loaded_from_disk = False
                return False

            # The sidecar is a versioned envelope: {"version", "chunks", ...}.
            if isinstance(payload, dict):
                records = payload.get("chunks")
            elif isinstance(payload, list):  # legacy: bare list
                records = payload
            else:
                records = None

            if not isinstance(records, list) or not records:
                logger.error(
                    "faiss_load_failed",
                    extra={"error": "metadata sidecar contains no chunks"},
                )
                self._index = None
                self._records = []
                self._dimension = 0
                self._index_type = ""
                self._loaded_from_disk = False
                return False
            if index.ntotal != len(records):
                logger.error(
                    "faiss_load_failed",
                    extra={
                        "error": "index/metadata chunk count mismatch",
                        "index_ntotal": int(index.ntotal),
                        "metadata_chunks": len(records),
                    },
                )
                self._index = None
                self._records = []
                self._dimension = 0
                self._index_type = ""
                self._loaded_from_disk = False
                return False

            self._index = index
            self._records = records
            self._dimension = int(index.d)
            self._index_type = type(index).__name__
            self._loaded_from_disk = True
            logger.info(
                "faiss_loaded",
                extra={"chunks": len(records), "documents": self.total_documents, "dimension": self._dimension},
            )
            return True

    def save(self) -> None:
        """Persist the index and metadata sidecar."""
        if not FAISS_AVAILABLE or self._index is None:
            return
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            _faiss.write_index(self._index, str(self.index_path))
            payload = {
                "version": 1,
                "dimension": self._dimension,
                "index_type": self._index_type,
                "similarity_metric": self.similarity_metric,
                "encoder": embedding_service.info().model_dump(),
                "total_documents": self.total_documents,
                "total_chunks": self.total_chunks,
                "chunks": self._records,
            }
            self.metadata_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def reset(self) -> None:
        with self._lock:
            self._index = None
            self._records = []
            self._vectors = []
            self._dimension = 0
            self._index_type = ""
            self._loaded_from_disk = False

    # ----------------------------------------------------------------- build
    def _create_index(self, dimension: int) -> Any:
        """Create a cosine-similarity index of the configured family."""
        settings = get_settings()
        kind = (settings.FAISS_INDEX_TYPE or "Flat").lower()
        if kind == "hnsw":
            # IndexHNSWFlat does not normalize internally, but our vectors are
            # already L2-normalized so inner product == cosine.
            return _faiss.IndexHNSWFlat(dimension, 32, _faiss.METRIC_INNER_PRODUCT)
        if kind == "ivf":
            nlist = max(int(4 * math.sqrt(1)), 1)
            quantizer = _faiss.IndexFlatIP(dimension)
            index = _faiss.IndexIVFFlat(quantizer, dimension, nlist, _faiss.METRIC_INNER_PRODUCT)
            return index
        return _faiss.IndexFlatIP(dimension)

    async def ingest(
        self,
        documents: Sequence[Dict[str, Any]],
        *,
        rebuild: bool = False,
    ) -> Dict[str, Any]:
        """Chunk, embed and index authorized local documents.

        Each document dict requires ``title`` and either ``text`` or
        ``source_path``. Returns a summary plus per-document results.
        """
        if not FAISS_AVAILABLE:
            raise AppError(
                ErrorCode.FAISS_INDEX_MISSING,
                "FAISS is not installed. Install 'faiss-cpu' to build the retrieval index.",
                status_code=503,
            )
        settings = get_settings()

        results: List[Dict[str, Any]] = []
        prepared: List[Dict[str, Any]] = []

        for index, document in enumerate(documents):
            title = str(document.get("title") or "").strip()
            if not title:
                results.append(
                    {
                        "document_id": document.get("document_id") or f"doc-{index}",
                        "title": "",
                        "chunks": 0,
                        "status": "skipped",
                        "reason": "missing title",
                    }
                )
                continue

            text = str(document.get("text") or "").strip()
            if not text and document.get("source_path"):
                text = self._read_knowledge_file(str(document["source_path"]))
            if not text:
                results.append(
                    {
                        "document_id": document.get("document_id") or f"doc-{index}",
                        "title": title,
                        "chunks": 0,
                        "status": "skipped",
                        "reason": "no readable text content",
                    }
                )
                continue

            chunks = chunk_text(text)
            if not chunks:
                results.append(
                    {
                        "document_id": document.get("document_id") or f"doc-{index}",
                        "title": title,
                        "chunks": 0,
                        "status": "skipped",
                        "reason": "text produced no chunks",
                    }
                )
                continue

            document_id = str(document.get("document_id") or f"doc-{uuid.uuid4().hex[:8]}")
            for chunk_index, chunk in enumerate(chunks):
                prepared.append(
                    {
                        "document_id": document_id,
                        "title": title,
                        "source": str(document.get("source") or "local"),
                        "pmid": document.get("pmid"),
                        "doi": document.get("doi"),
                        "society": document.get("society"),
                        "publication_year": document.get("publication_year"),
                        "chunk_index": chunk_index,
                        "text": chunk,
                        "metadata": {
                            **(document.get("metadata") or {}),
                            "chunk_id": f"{document_id}#c{chunk_index}",
                            "char_start": None,
                        },
                    }
                )
            results.append(
                {
                    "document_id": document_id,
                    "title": title,
                    "chunks": len(chunks),
                    "status": "indexed",
                    "reason": "",
                }
            )

        if not prepared:
            return {
                "documents_indexed": 0,
                "chunks_indexed": 0,
                "total_documents": self.total_documents,
                "total_chunks": self.total_chunks,
                "results": results,
                "warnings": ["No document produced indexable chunks; the index was left unchanged."],
                "index_status": self.status(),
            }

        vectors = await embedding_service.embed([record["text"] for record in prepared])
        matrix = l2_normalize(vectors)
        dimension = int(matrix.shape[1])
        warnings: List[str] = []

        with self._lock:
            # An index loaded from disk has no in-memory vectors, so a partial
            # replacement is not possible. Rebuild explicitly instead of
            # leaving the index inconsistent with its metadata.
            vectors_available = len(self._vectors) == len(self._records)
            if self._records and not vectors_available and not rebuild:
                warnings.append(
                    "Index was loaded from disk; a full rebuild was performed because "
                    "in-memory vectors were unavailable for a partial update."
                )
                rebuild = True
            if rebuild or self._index is None or self._dimension != dimension:
                self._index = self._create_index(dimension)
                self._dimension = dimension
                self._index_type = type(self._index).__name__
                self._records = []
                self._vectors = []
            else:
                # Re-ingested documents replace their previous chunks.
                replaced = {
                    record["document_id"]
                    for record in prepared
                    if any(result.get("document_id") == record["document_id"] for result in results)
                }
                if replaced:
                    keep = [i for i, r in enumerate(self._records) if r.get("document_id") not in replaced]
                    retained_records = [self._records[i] for i in keep]
                    retained_vectors = [self._vectors[i] for i in keep] if self._vectors else []
                    if retained_vectors and len(retained_vectors) == len(keep):
                        self._rebuild_locked(retained_records, retained_vectors, matrix)
                    else:
                        self._records = []
                        self._vectors = []

            if not self._records and self._dimension == dimension:
                self._index = self._create_index(dimension)
                self._index_type = type(self._index).__name__

            self._add_locked(matrix)
            self._records.extend(prepared)
            self._vectors.extend([row.tolist() for row in matrix])

        self.save()
        indexed_count = sum(1 for r in results if r.get("status") == "indexed")
        logger.info(
            "faiss_ingested",
            extra={
                "documents": indexed_count,
                "chunks": len(prepared),
                "total_documents": self.total_documents,
                "total_chunks": self.total_chunks,
                "dimension": self._dimension,
            },
        )
        return {
            "documents_indexed": indexed_count,
            "chunks_indexed": len(prepared),
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "results": results,
            "warnings": warnings,
            "index_status": self.status(),
        }

    def _add_locked(self, matrix: np.ndarray) -> None:
        """Add vectors, training first when the index family requires it."""
        if matrix.size == 0:
            return
        try:
            self._index.add(matrix)
        except Exception as exc:
            # IVF families must be trained before vectors can be added.
            try:
                self._index.train(matrix)
                self._index.add(matrix)
            except Exception as inner:
                logger.error(
                    "faiss_add_failed",
                    extra={"error": str(inner)[:300], "first_error": str(exc)[:300]},
                )
                raise AppError(
                    ErrorCode.FAISS_INDEX_MISSING,
                    f"Failed to add vectors to the FAISS index: {inner}",
                    status_code=500,
                ) from inner

    def _rebuild_locked(
        self, records: List[Dict[str, Any]], vectors: List[List[float]], new_matrix: np.ndarray
    ) -> None:
        """Recreate the index from retained in-memory vectors plus new ones."""
        self._records = records
        self._index = self._create_index(self._dimension)
        self._index_type = type(self._index).__name__
        self._vectors = [list(v) for v in vectors]
        if vectors:
            self._add_locked(l2_normalize(vectors))

    def _read_knowledge_file(self, relative_path: str) -> str:
        """Read a local text file from the knowledge directory.

        Path traversal outside the knowledge directory is rejected.
        """
        settings = get_settings()
        root = settings.knowledge_dir.resolve()
        candidate = Path(relative_path)
        target = (candidate if candidate.is_absolute() else root / candidate).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise AppError(
                ErrorCode.INVALID_FILE,
                "source_path must stay inside the configured knowledge directory.",
                status_code=400,
            ) from exc
        if not target.exists() or not target.is_file():
            return ""
        if target.suffix.lower() not in {".txt", ".md", ".markdown", ".json"}:
            return ""
        content = target.read_text(encoding="utf-8", errors="replace")
        if target.suffix.lower() == ".json":
            try:
                payload = json.loads(content)
                if isinstance(payload, dict):
                    return str(payload.get("text") or payload.get("content") or content)
            except json.JSONDecodeError:
                return content
        return content

    # ---------------------------------------------------------------- search
    async def search(
        self,
        query: str = "",
        *,
        top_k: Optional[int] = None,
        latent_query: Optional[Sequence[float]] = None,
        societies: Optional[Iterable[str]] = None,
        min_similarity: float = 0.0,
        include_text: bool = True,
    ) -> Dict[str, Any]:
        """Search the index. Returns evidence plus an index status block."""
        settings = get_settings()
        k = top_k or settings.RETRIEVAL_TOP_K

        if not FAISS_AVAILABLE:
            return {
                "evidence": [],
                "index_status": "unavailable",
                "knowledge_base_initialized": False,
                "message": "FAISS is not installed; retrieval is unavailable.",
                "error": {
                    "code": ErrorCode.FAISS_INDEX_MISSING,
                    "message": "FAISS is not installed. Install 'faiss-cpu'.",
                },
            }

        if not self.initialized:
            self.load()

        if not self.initialized:
            return {
                "evidence": [],
                "index_status": "uninitialized",
                "knowledge_base_initialized": False,
                "message": "Knowledge base not initialized",
                "error": None,
            }

        if latent_query is not None:
            vector = np.asarray([latent_query], dtype=np.float32)
        else:
            if not (query or "").strip():
                return {
                    "evidence": [],
                    "index_status": "ready",
                    "knowledge_base_initialized": True,
                    "message": "Empty query; no search performed.",
                    "error": None,
                }
            vector = np.asarray([await embedding_service.embed_one(query)], dtype=np.float32)

        if vector.shape[1] != self._dimension:
            return {
                "evidence": [],
                "index_status": "dimension_mismatch",
                "knowledge_base_initialized": True,
                "message": (
                    f"Query vector has dimension {vector.shape[1]} but the index expects "
                    f"{self._dimension}. Rebuild the index or align the encoder."
                ),
                "error": {
                    "code": ErrorCode.EMBEDDING_MODEL_UNAVAILABLE,
                    "message": "Embedding dimension does not match the FAISS index.",
                },
            }

        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector = vector / norm

        with self._lock:
            search_k = min(max(k * 4, k), max(self.total_chunks, 1))
            try:
                scores, indices = self._index.search(vector, search_k)
            except Exception as exc:
                logger.error("faiss_search_failed", extra={"error": str(exc)[:300]})
                return {
                    "evidence": [],
                    "index_status": "error",
                    "knowledge_base_initialized": True,
                    "message": "FAISS search failed.",
                    "error": {
                        "code": ErrorCode.FAISS_INDEX_MISSING,
                        "message": f"FAISS search failed: {exc}",
                    },
                }
            records_snapshot = list(self._records)

        wanted = {s.strip().lower() for s in societies} if societies else set()
        evidence: List[RetrievedEvidence] = []
        for score, position in zip(scores[0], indices[0]):
            if position < 0 or position >= len(records_snapshot):
                continue
            record = records_snapshot[int(position)]
            society = record.get("society")
            if wanted and str(society or "").strip().lower() not in wanted:
                continue
            similarity = float(score)
            if similarity < min_similarity:
                continue
            evidence.append(
                RetrievedEvidence(
                    document_id=str(record.get("document_id", "")),
                    title=str(record.get("title", "")),
                    source=str(record.get("source", "local")),
                    chunk_id=str((record.get("metadata") or {}).get("chunk_id", "")),
                    text=str(record.get("text", "")) if include_text else "",
                    similarity=round(similarity, 6),
                    metadata=dict(record.get("metadata") or {}),
                    pmid=record.get("pmid"),
                    doi=record.get("doi"),
                    society=society,
                    publication_year=record.get("publication_year"),
                    chunk_index=record.get("chunk_index"),
                )
            )
            if len(evidence) >= k:
                break

        return {
            "evidence": evidence,
            "index_status": "ready",
            "knowledge_base_initialized": True,
            "message": None,
            "error": None,
        }


retrieval_service = RetrievalService()
