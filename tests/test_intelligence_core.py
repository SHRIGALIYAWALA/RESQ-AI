from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_existing_incident_intelligence_is_persisted():
    incident = client.post(
        "/api/incidents",
        json={
            "title": "Smoke report",
            "incident_type": "fire",
            "description": "Smoke reported near the lobby",
            "location": {"floor": 1, "room": "Lobby"},
        },
    )
    assert incident.status_code == 200, incident.text
    incident_id = incident.json()["id"]

    response = client.post(f"/api/incidents/{incident_id}/intelligence")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["incident_id"] == incident_id
    assert body["status"] == "analysis_persisted"
    assert body["analysis"]["decision"]["human_approval_required"] is True
    assert body["analysis"]["report"]["limitations"]

    stored = client.get(f"/api/incidents/{incident_id}")
    assert stored.status_code == 200, stored.text
    assert "priority incident requiring human review" in stored.json()["summary"]
