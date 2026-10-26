import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_announcements_generation_and_approval():
    # 1. Generate multilingual announcement
    payload = {
        "building_id": 1,
        "text_en": "Attention: Fire emergency detected. Proceed to Exit A.",
        "text_hi": "कृपया ध्यान दें: आग की आपातकालीन स्थिति।",
        "text_gu": "કૃપા કરીને ધ્યાન આપો: આગ લાગવાની કટોકટી છે.",
    }
    response = client.post("/api/announcements/generate", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "PENDING_OPERATOR_APPROVAL"
    announcement_id = data["id"]

    # 2. Approve announcement by operator
    app_res = client.post(f"/api/announcements/{announcement_id}/approve", json={"operator": "Chief Operator"})
    assert app_res.status_code == 200, app_res.text
    app_data = app_res.json()
    assert app_data["status"] == "broadcast_released"
    assert app_data["announcement"]["status"] == "APPROVED_AND_BROADCASTED"
    assert app_data["announcement"]["approved_by"] == "Chief Operator"
