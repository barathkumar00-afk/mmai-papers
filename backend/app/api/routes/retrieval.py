"""``POST /api/retrieve/evidence`` and ``POST /api/retrieve/ingest``.

Retrieval never fabricates citations: when the FAISS index is absent or empty the
response states ``Knowledge base not initialized`` and returns no evidence.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.common import Provenance, Uncertainty
from app.schemas.retrieval import (
    EvidenceQueryRequest,
    EvidenceResponse,
    IndexStatus,
    IngestRequest,
    IngestResponse,
    RetrievedEvidence,
)
from app.services.embedding_service import embedding_service
from app.services.retrieval_service import retrieval_service

router = APIRouter(tags=["Retrieval"])
logger = get_logger(__name__)

NOT_INITIALIZED = "Knowledge base not initialized"


@router.post(
    "/evidence",
    response_model=EvidenceResponse,
    summary="Search the local FAISS medical knowledge base",
)
async def retrieve_evidence(request: EvidenceQueryRequest) -> EvidenceResponse:
    started = time.perf_counter()
    rid = uuid.uuid4().hex[:12]

    result = await retrieval_service.search(
        request.query,
        top_k=request.top_k,
        latent_query=request.latent_query,
        societies=request.societies,
        min_similarity=request.min_similarity,
        include_text=request.include_text,
    )

    evidence: list = result.get("evidence") or []
    error = result.get("error")
    message = result.get("message")

    encoder = embedding_service.info()
    return EvidenceResponse(
        success=True,
        query=request.query,
        top_k=request.top_k,
        evidence=evidence,
        citations=[_to_citation(item, index) for index, item in enumerate(evidence)],
        index_status=str(result.get("index_status", "uninitialized")),
        knowledge_base_initialized=bool(result.get("knowledge_base_initialized")),
        message=message
        or (NOT_INITIALIZED if not evidence and not result.get("knowledge_base_initialized") else None),
        encoder=encoder,
        provenance=Provenance(
            mode="real",
            label=_retrieval_label(encoder, bool(evidence)),
            computed_by=f"faiss:{result.get('index_status', 'unknown')}",
            simulated=False,
            notes=(
                (
                    f"Similarity values are cosine similarities between the query and the "
                    f"stored chunk, using the '{encoder.name}' encoder. They are retrieval "
                    f"scores, not measures of clinical relevance or accuracy."
                )
                if evidence
                else "No evidence was retrieved. No citations are fabricated."
            ),
        ),
        request_id=rid,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        error=error,
    )


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest authorized local documents into the FAISS index",
)
async def ingest_documents(request: IngestRequest) -> IngestResponse:
    started = time.perf_counter()
    rid = uuid.uuid4().hex[:12]

    documents: list[Dict[str, Any]] = [doc.model_dump(exclude_none=False) for doc in request.documents]
    summary = await retrieval_service.ingest(documents, rebuild=request.rebuild)
    status = summary.get("index_status", {})

    return IngestResponse(
        success=True,
        index_status="ready" if status.get("initialized") else "uninitialized",
        documents_indexed=summary.get("documents_indexed", 0),
        chunks_indexed=summary.get("chunks_indexed", 0),
        total_documents=summary.get("total_documents", 0),
        total_chunks=summary.get("total_chunks", 0),
        results=summary.get("results", []),
        embedding_dimension=int(status.get("dimension", 0)),
        similarity_metric=str(status.get("similarity_metric", "cosine")),
        index_type=str(status.get("index_type", "")),
        warnings=summary.get("warnings", []),
        request_id=rid,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


@router.get("/status", response_model=IndexStatus, summary="FAISS index status")
async def index_status() -> IndexStatus:
    state = retrieval_service.status()
    initialized = bool(state.get("initialized"))
    encoder = embedding_service.info()

    return IndexStatus(
        initialized=initialized,
        index_path=str(state.get("index_path")),
        metadata_path=str(state.get("metadata_path")),
        total_documents=int(state.get("total_documents", 0)),
        total_chunks=int(state.get("total_chunks", 0)),
        dimension=int(state.get("dimension", 0)),
        index_type=str(state.get("index_type", "")),
        similarity_metric=str(state.get("similarity_metric", "cosine")),
        encoder=encoder,
        uncertainty=Uncertainty(
            overall=0.0 if initialized else 0.5,
            confidence=1.0 if initialized else 0.5,
            drivers=(
                ["FAISS index is loaded and searchable."]
                if initialized
                else ["FAISS index is not initialized; run the ingestion script or POST /api/retrieve/ingest."]
            ),
            missing_information=[] if initialized else ["An initialized knowledge base."],
        ),
        message=None if initialized else NOT_INITIALIZED,
    )


def _retrieval_label(encoder: Any, has_evidence: bool) -> str:
    """Never claim more than the configured encoder supports.

    A hashing / bag-of-words encoder produces a genuine local FAISS search, but
    the ranking is lexical rather than semantic. Labelling that "semantic
    retrieval" would misrepresent the system, so the encoder class is named.
    """
    if not has_evidence:
        return "LOCAL RETRIEVAL (NO EVIDENCE)"
    name = str(getattr(encoder, "name", "") or "").lower()
    if "hash" in name or "bag" in name:
        return "REAL LOCAL FAISS RETRIEVAL (LEXICAL HASHING ENCODER)"
    if getattr(encoder, "status", "") in {"unavailable", "unconfigured"}:
        return "REAL LOCAL FAISS RETRIEVAL (ENCODER DEGRADED)"
    return "REAL LOCAL FAISS RETRIEVAL"


def _to_citation(item: RetrievedEvidence, index: int) -> Dict[str, Any]:
    """Shape a retrieved chunk for the frontend evidence cards.

    Field names and types match what the existing ``EvidenceSection`` renders:
    ``id``, ``title``, ``relevance``, ``quote``, ``pmid``, ``journal``.
    """
    import uuid as _uuid

    return {
        "id": item.chunk_id or f"c{index}-{_uuid.uuid4().hex[:6]}",
        "document_id": item.document_id,
        "title": item.title or item.chunk_id or "Untitled source",
        # A retrieval score, not a research metric. Labelled for the UI.
        "relevance": f"{max(item.similarity, 0.0) * 100:.1f}%",
        "similarity": round(item.similarity, 6),
        "similarity_basis": "faiss_cosine_similarity (retrieval score, not clinical relevance)",
        "quote": item.text,
        "pmid": f"PMID: {item.pmid}" if item.pmid else (item.doi or f"local:{item.source}"),
        "journal": item.society or item.source or "local",
        "publication_year": item.publication_year,
        "source": item.source,
        "is_simulated": False,
    }
