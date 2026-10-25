"""Schemas for evidence retrieval (FAISS) and knowledge-base ingestion."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ModelInfo, Provenance, Uncertainty


class RetrievedEvidence(BaseModel):
    """A single retrieved chunk.

    Every field is populated from the local knowledge store. If the store is
    empty, no evidence objects are returned at all -- never fabricated ones.
    """

    document_id: str
    title: str = ""
    source: str = ""
    chunk_id: str = ""
    text: str = ""
    similarity: float = Field(0.0, ge=-1.0, le=1.0, description="Cosine similarity in [-1,1]")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    pmid: Optional[str] = None
    doi: Optional[str] = None
    society: Optional[str] = None
    publication_year: Optional[int] = None
    chunk_index: Optional[int] = None


class EvidenceQueryRequest(BaseModel):
    """Accepts natural-language text and/or an explicit vector."""

    query: str = Field("", description="Natural-language clinical query")
    latent_query: Optional[List[float]] = Field(
        None, description="Optional pre-computed embedding (skips the encoder)"
    )
    top_k: int = Field(5, ge=1, le=25)
    societies: List[str] = Field(default_factory=list, description="Optional source filters")
    min_similarity: float = Field(0.0, ge=-1.0, le=1.0)
    include_text: bool = True

    @field_validator("query", mode="before")
    @classmethod
    def _coerce(cls, value: Any) -> str:
        return str(value or "").strip()[:5000]

    @field_validator("societies", mode="before")
    @classmethod
    def _societies(cls, value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("latent_query")
    @classmethod
    def _check_vector(cls, value: Optional[List[float]]) -> Optional[List[float]]:
        if value is None:
            return None
        if len(value) < 8:
            raise ValueError("latent_query must contain at least 8 dimensions")
        if len(value) > 8192:
            raise ValueError("latent_query exceeds the maximum supported dimensionality")
        return value


class EvidenceResponse(BaseModel):
    success: bool = True
    query: str = ""
    top_k: int = 5
    evidence: List[RetrievedEvidence] = Field(default_factory=list)
    #: Shape compatible with the frontend EvidenceSection citation cards.
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    index_status: str = "uninitialized"
    knowledge_base_initialized: bool = False
    message: Optional[str] = Field(
        None, description="Set to 'Knowledge base not initialized' when no index exists"
    )
    encoder: ModelInfo
    provenance: Provenance
    request_id: str = ""
    latency_ms: float = 0.0
    error: Optional[Dict[str, Any]] = None


class IngestDocument(BaseModel):
    """A single authorized local document to add to the knowledge base."""

    document_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    text: Optional[str] = Field(None, description="Inline document text; omit when source_path is used")
    source_path: Optional[str] = Field(
        None, description="Path to a local .txt/.md/.json file, relative to the knowledge directory"
    )
    source: str = "local"
    pmid: Optional[str] = None
    doi: Optional[str] = None
    society: Optional[str] = None
    publication_year: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: List[IngestDocument] = Field(..., min_length=1, max_length=500)
    rebuild: bool = Field(False, description="Discard the existing index and rebuild from scratch")


class IngestResult(BaseModel):
    document_id: str
    title: str
    chunks: int
    status: str
    reason: str = ""


class IngestResponse(BaseModel):
    success: bool = True
    index_status: str = "ready"
    documents_indexed: int = 0
    chunks_indexed: int = 0
    total_documents: int = 0
    total_chunks: int = 0
    results: List[IngestResult] = Field(default_factory=list)
    embedding_dimension: int = 0
    similarity_metric: str = "cosine"
    index_type: str = "Flat"
    warnings: List[str] = Field(default_factory=list)
    request_id: str = ""
    latency_ms: float = 0.0
    error: Optional[Dict[str, Any]] = None


class IndexStatus(BaseModel):
    initialized: bool
    index_path: str
    metadata_path: str
    total_documents: int = 0
    total_chunks: int = 0
    dimension: int = 0
    index_type: str = ""
    similarity_metric: str = "cosine"
    encoder: ModelInfo
    uncertainty: Uncertainty
    message: Optional[str] = None
