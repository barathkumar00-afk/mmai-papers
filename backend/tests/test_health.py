"""Health, service banner and error-envelope contract tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_banner(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "online"
    assert "health" in payload
    # Clinical safety positioning must always be advertised.
    assert "Not an autonomous diagnosis" in payload["clinical_positioning"]


def test_health_reports_dependencies(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] in {"online", "degraded"}
    assert payload["service"]
    assert payload["version"]

    # Every dependency block must be present and honestly labelled.
    for key in ("ollama", "retrieval", "models"):
        assert key in payload, f"health response is missing '{key}'"

    assert "simulated" in payload["ollama"]["status"] or payload["ollama"]["model_exists"]
    assert payload["retrieval"]["faiss_installed"] is True


def test_health_declares_fusion_is_not_a_trained_model(client: TestClient) -> None:
    """The system must not misrepresent its fusion layer."""
    response = client.get("/api/health")
    fusion = response.json()["models"]["fusion"]
    assert fusion["role"] == "integration_layer"
    assert "trained" in fusion["note"].lower()


def test_health_readiness_detail(client: TestClient) -> None:
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert "ready" in payload
    assert isinstance(payload["notes"], list)


def test_request_id_header_is_echoed_or_generated(client: TestClient) -> None:
    supplied = client.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert supplied.headers["X-Request-ID"] == "abc123"

    generated = client.get("/api/health")
    assert generated.headers["X-Request-ID"]


def test_unknown_route_returns_structured_error(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"]
    assert payload["error"]["message"]


def test_openapi_schema_is_generated(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = set(schema["paths"])
    for required in (
        "/api/health",
        "/api/analyze/image",
        "/api/analyze/speech",
        "/api/analyze/clinical",
        "/api/analyze/multimodal",
        "/api/retrieve/evidence",
        "/api/retrieve/ingest",
        "/api/generate/explanation",
        "/api/generate/report",
    ):
        assert required in paths, f"missing documented endpoint {required}"
