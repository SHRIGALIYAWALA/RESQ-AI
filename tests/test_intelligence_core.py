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
    assert "priority incident requiring human review" in stored.json()["summary"].lower()


def test_incident_analyze_returns_recommendations_in_supported_shape(monkeypatch):
    import backend.api.incidents as incidents_api

    async def fake_analyze_async(incident, building=None):
        return {
            "status": "analysis_complete",
            "incident_classification": {
                "classification": {
                    "summary": "Smoke reported near the lobby.",
                    "recommended_actions": ["Verify the reported conditions."],
                },
            },
            "evacuation_plan": {
                "primary_safe_exits": ["North Exit"],
                "room_instructions": {"Lobby": "Use North Exit."},
            },
            "communications": {
                "announcement_script_en": "Please use North Exit.",
            },
            "human_authorization_required": True,
        }

    monkeypatch.setattr(incidents_api.core_agent, "analyze_async", fake_analyze_async)
    incident = client.post(
        "/api/incidents",
        json={
            "title": "Smoke report for analysis contract",
            "incident_type": "fire",
            "description": "Smoke reported near the lobby",
            "location": {"floor": 1, "room": "Lobby"},
        },
    )
    assert incident.status_code == 200, incident.text

    response = client.post(f"/api/incidents/{incident.json()['id']}/analyze")

    assert response.status_code == 200, response.text
    analysis = response.json()["analysis"]
    assert analysis["incident_classification"]["classification"]["recommended_actions"]
    assert analysis["evacuation_plan"]["primary_safe_exits"] == ["North Exit"]
    assert analysis["communications"]["announcement_script_en"] == "Please use North Exit."
    assert analysis["human_authorization_required"] is True
