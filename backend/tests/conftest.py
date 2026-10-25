"""Shared pytest fixtures.

The whole suite runs in ``MOCK_MODE`` with a temporary data directory so that
no test ever touches the developer's real index, and so that no test can
silently depend on a running Ollama instance.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _environment() -> Iterator[None]:
    """Force mock mode and an isolated data directory for the session."""
    os.environ["MOCK_MODE"] = "true"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["OLLAMA_LLM_MODEL"] = "test-llm"
    os.environ["OLLAMA_VISION_MODEL"] = ""
    os.environ["EMBEDDING_PROVIDER"] = "hashing"
    os.environ.pop("OLLAMA_EMBEDDING_MODEL", None)
    yield


@pytest.fixture(scope="session")
def client(_environment: None) -> Iterator["TestClient"]:  # noqa: F821
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def clean_index() -> Iterator[None]:
    """Give a test an empty knowledge base and restore the previous state."""
    from app.services.retrieval_service import retrieval_service

    previous_index = retrieval_service._index
    previous_records = list(retrieval_service._records)
    previous_dimension = retrieval_service._dimension
    previous_type = retrieval_service._index_type

    retrieval_service.reset()
    yield
    retrieval_service._index = previous_index
    retrieval_service._records = previous_records
    retrieval_service._dimension = previous_dimension
    retrieval_service._index_type = previous_type
