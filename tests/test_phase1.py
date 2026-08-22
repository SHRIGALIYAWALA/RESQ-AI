from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_building_and_incident():
    building = client.post(
        "/api/buildings",
        json={
            "name": "RESQ Demo Building",
            "address": "123 Demo Street",
            "floors": [{"name": "Floor 1", "number": 1}, {"name": "Floor 2", "number": 2}],
            "rooms": [{"name": "Lobby", "floor_number": 1}, {"name": "Lab 201", "floor_number": 2}],
        },
    )
    assert building.status_code == 200, building.text
    building_id = building.json()["id"]

    incident = client.post(
        "/api/incidents",
        json={
            "title": "Fire on floor 2",
            "incident_type": "fire",
            "description": "Smoke seen near Lab 201",
            "building_id": building_id,
            "location": {"floor": 2, "room": "Lab 201"},
        },
    )
    assert incident.status_code == 200, incident.text
    body = incident.json()
    assert body["incident_type"] == "fire"
    assert body["building_id"] == building_id


def test_ai_analysis_endpoint():
    payload = {
        "title": "Medical emergency in auditorium",
        "incident_type": "medical",
        "description": "Person collapsed near auditorium entrance",
        "building_id": 1,
        "location": {"floor": 1, "room": "Auditorium"},
    }
    response = client.post("/api/incidents/analyze", json=payload)
    assert response.status_code == 200
    payload_response = response.json()
    assert "planner" in payload_response
    assert "triage" in payload_response
