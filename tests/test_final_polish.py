"""Tests for PDF parsing, metrics, and optional live webcam."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.media_adapters import MediaInspector

client = TestClient(app)


def _has_webcam_windows() -> bool:
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ok = cap.isOpened()
        cap.release()
        return ok
    except Exception:
        return False


def test_pdf_inspection_with_minimal_pdf(tmp_path: Path):
    pdf_path = tmp_path / "floor_plan.pdf"
    # Minimal valid PDF with text stream
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 200 200]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 50 150 Td (Emergency exit fire) Tj ET\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    result = MediaInspector().inspect(pdf_path, "pdf")
    assert result["media_type"] == "pdf"
    assert result["status"] in {"provider_result", "provider_unavailable"}
    if result["status"] == "provider_result":
        assert "fire" in result.get("keywords_detected", []) or "exit" in result.get("keywords_detected", [])


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "resq-ai"
    assert "database_ok" in data


def test_legacy_html_fallback():
    response = client.get("/legacy", follow_redirects=False)
    assert response.status_code == 200


@pytest.mark.skipif(not Path("/dev/video0").exists() and not _has_webcam_windows(), reason="No webcam available")
def test_live_webcam_registration():
    """Register webcam source 0 when hardware is present."""
    response = client.post("/api/cameras", json={
        "name": "Live Webcam Test",
        "source": "0",
        "zone": "Test Zone",
        "floor_number": 1,
        "building_id": 1,
    })
    assert response.status_code == 200, response.text
    cam_id = response.json()["id"]
    snapshot = client.get(f"/api/cameras/{cam_id}/snapshot")
    assert snapshot.status_code in {200, 503}
