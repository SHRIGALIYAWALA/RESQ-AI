from io import BytesIO
import uuid

from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from backend.config import get_settings

client = TestClient(app)


def test_mobile_camera_photo_is_stored_with_incident_and_deletable(monkeypatch, tmp_path):
    import backend.api.incidents as incidents_api

    monkeypatch.setattr(incidents_api.settings, "upload_dir", str(tmp_path))
    incident = client.post(
        "/api/incidents",
        json={
            "title": "Mobile camera evidence test",
            "incident_type": "fire",
            "description": "Test image evidence association",
            "location": {"floor": 1},
        },
    )
    assert incident.status_code == 200, incident.text
    incident_id = incident.json()["id"]

    image_bytes = BytesIO()
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(image_bytes, format="PNG")
    upload = client.post(
        f"/api/incidents/{incident_id}/media",
        files={"file": ("capture.png", image_bytes.getvalue(), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    media_id = upload.json()["media_id"]
    assert upload.json()["incident_id"] == incident_id
    assert upload.json()["review_required"] is True

    image = client.get(f"/api/incidents/{incident_id}/media/{media_id}")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    assert image.content.startswith(b"\xff\xd8")

    deleted = client.delete(f"/api/incidents/{incident_id}/media/{media_id}")
    assert deleted.status_code == 200, deleted.text
    assert not (tmp_path / "incidents" / str(incident_id) / f"{media_id}.jpg").exists()
    missing = client.get(f"/api/incidents/{incident_id}/media/{media_id}")
    assert missing.status_code == 404


def test_browser_auth_uses_http_only_cookie(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "require_auth", True)
    username = f"mobile-test-{uuid.uuid4().hex[:10]}"
    password = "camera-test-password"

    registration = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "role": "operator"},
    )
    assert registration.status_code == 200, registration.text

    unauthenticated = client.get("/api/cameras")
    assert unauthenticated.status_code == 401

    login = client.post("/api/auth/token", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert login.json()["access_token"]
    assert client.get("/api/auth/session").json()["authenticated"] is True
    assert client.get("/api/cameras").status_code == 200

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/session").json()["authenticated"] is False
