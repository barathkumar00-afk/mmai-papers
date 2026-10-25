"""Aggregated API router.

Prefix layout::

    /api/health                 service + dependency health
    /api/analyze/image          image analysis
    /api/analyze/speech         speech analysis
    /api/analyze/clinical       clinical text normalization
    /api/analyze/multimodal     full multimodal pipeline
    /api/retrieve/evidence      FAISS evidence retrieval
    /api/retrieve/ingest        knowledge-base ingestion
    /api/retrieve/status        FAISS index status
    /api/generate/explanation   evidence trail
    /api/generate/report        14-section clinical report
    /api/v2/*                   compatibility layer for the documented contracts
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    clinical,
    explanation,
    health,
    image,
    multimodal,
    report,
    retrieval,
    speech,
    v2,
)

router = APIRouter()

# ---- health
router.include_router(health.router, prefix="/health", tags=["Health"])

# ---- analysis
router.include_router(image.router, prefix="/analyze", tags=["Image Analysis"])
router.include_router(speech.router, prefix="/analyze", tags=["Speech Analysis"])
router.include_router(clinical.router, prefix="/analyze", tags=["Clinical Analysis"])
router.include_router(multimodal.router, prefix="/analyze", tags=["Multimodal"])

# ---- retrieval
router.include_router(retrieval.router, prefix="/retrieve", tags=["Retrieval"])

# ---- generation
router.include_router(explanation.router, prefix="/generate", tags=["Explainability"])
router.include_router(report.router, prefix="/generate", tags=["Reporting"])

# ---- frontend-documented compatibility contracts
router.include_router(v2.router, prefix="/v2")
