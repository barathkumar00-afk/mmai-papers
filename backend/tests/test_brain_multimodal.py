"""Integration and edge-case test suite for Brain Disease AI multimodal decision support."""

import io
from pathlib import Path
from starlette.testclient import TestClient

def test_multimodal_brain_glioma_analysis(client: TestClient) -> None:
    """A valid brain MRI with neurological symptoms returns structured differential ranking."""
    img_path = Path("data/samples/sample_brain_glioma.png")
    if not img_path.exists():
        img_path = Path("test_image.jpg")
    
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    
    response = client.post(
        "/api/analyze/multimodal",
        files={"image": ("Brain_MRI_Axial_Glioma.png", img_bytes, "image/png")},
        data={
            "case_id": "#NEURO-TEST-001",
            "complaint": "Progressive morning headache and focal motor seizures.",
            "spo2": "98%",
            "crp": "3.5",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Glioma" in data["primary_finding"]
    assert len(data["differential_ranking"]) >= 3
    assert any("Glioma" in c["label"] for c in data["differential_ranking"])
    assert any("Meningioma" in c["label"] for c in data["differential_ranking"])
    assert len(data["recommendations"]) > 0
    assert data["confidence"] > 0.0
    assert data["uncertainty"] > 0.0
    assert data["provenance"]["simulated"] is True or data["provenance"]["mode"] == "real"

def test_multimodal_missing_all_parameters(client: TestClient) -> None:
    """When no image, audio, or clinical data is provided, return 400 MISSING_PARAMETER."""
    response = client.post(
        "/api/analyze/multimodal",
        data={"case_id": "#EMPTY-CASE"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_PARAMETER"

def test_multimodal_unsupported_image_format(client: TestClient) -> None:
    """An unsupported payload (e.g. text file disguised as image) should fail validation."""
    fake_data = b"This is plain text pretending to be an image."
    response = client.post(
        "/api/analyze/multimodal",
        files={"image": ("fake.exe", fake_data, "application/octet-stream")},
        data={"complaint": "Headache"},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNSUPPORTED_FORMAT"

def test_multimodal_corrupted_image(client: TestClient) -> None:
    """Corrupted image header must be safely handled without server crash."""
    corrupted_png = b"\x89PNG\r\n\x1a\n" + b"Corrupted broken bytes"
    response = client.post(
        "/api/analyze/multimodal",
        files={"image": ("broken.png", corrupted_png, "image/png")},
        data={"complaint": "Seizure"},
    )
    # Backend either safely rejects with 400 INVALID_FILE or handles gracefully
    assert response.status_code in (400, 200)

def test_retrieval_neuro_oncology_faiss(client: TestClient) -> None:
    """Retrieval service retrieves neuro-oncology knowledge anchors from FAISS."""
    response = client.post(
        "/api/retrieve/evidence",
        json={"query": "Glioma IDH mutation WHO CNS 5 classification and T2 FLAIR"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["knowledge_base_initialized"] is True
    assert len(data["citations"]) > 0
    assert any("Glioma" in c["title"] or "Neuro" in c["title"] for c in data["citations"])
