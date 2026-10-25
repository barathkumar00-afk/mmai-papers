import httpx
from pathlib import Path

url = "http://127.0.0.1:8000/api/analyze/multimodal"
image_path = Path("test_image.jpg")
if not image_path.exists():
    image_path = Path("../test_image.jpg")

try:
    with open(image_path, "rb") as f:
        image_data = f.read()

    files = {
        "image": ("Brain_MRI_Axial_Glioma.png", image_data, "image/png"),
    }
    data = {
        "spo2": "98%",
        "crp": "4.2",
        "complaint": "Progressive morning headache, focal left-sided motor weakness, and new-onset focal seizure.",
        "case_id": "#NEURO-2026-0812",
    }

    print(f"Sending multimodal analysis request to {url}...")
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print("Error details:", response.text)
        payload = response.json()
        print("\nPrimary Finding:")
        print(payload.get("primary_finding"))
        print("\nDifferential Ranking:")
        for item in payload.get("differential_ranking", []):
            print(f"  {item.get('rank')}. {item.get('label')} (Weight: {item.get('weight')})")
        print("\nRecommendations:")
        for rec in payload.get("recommendations", []):
            print(f"  - {rec}")
        print("\nConfidence & Uncertainty:")
        print(f"  Confidence: {payload.get('confidence')} | Uncertainty: {payload.get('uncertainty')}")
        print("\nObserved Evidence Count:", len(payload.get("observed_evidence", [])))
        print("Retrieved Chunks Count:", len(payload.get("retrieved_evidence", [])))
except Exception as e:
    print(f"Error: {e}")
