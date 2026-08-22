from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_building_vision_and_live_environment_state():
    building = client.post(
        "/api/buildings",
        json={
            "name": "Vision Lab",
            "address": "4 Vision Lane",
            "description": "Vision test building",
            "floors": [{"number": 2, "name": "Second Floor"}],
            "rooms": [{"name": "Lab 203", "floor_number": 2, "zone": "research", "capacity": 20}],
            "cameras": [{"name": "C-04", "floor_number": 2, "location": "Corridor B", "zone": "east-wing", "direction": "north"}],
        },
    )
    building_id = building.json()["id"]

    response = client.post(
        f"/api/buildings/{building_id}/vision",
        json={
            "camera_id": "C-04",
            "observations": [
                "12 people detected",
                "smoke detected near corridor",
                "door partly blocked"
            ],
            "floor": 2,
            "zone": "east-wing",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["live_environment_state"]["building_id"] == building_id
    assert payload["live_environment_state"]["hazards"]


def test_multimodal_incident_input_creates_structured_context():
    incident = client.post(
        "/api/incidents",
        json={
            "title": "Fire alarm",
            "incident_type": "fire",
            "description": "Heavy smoke reported in the lab",
            "location": {"floor": 2, "room": "Lab 203"},
        },
    )
    incident_id = incident.json()["id"]

    response = client.post(
        f"/api/incidents/{incident_id}/multimodal",
        json={
            "text": "Fire in laboratory 203.",
            "voice": "There is smoke on the second floor.",
            "image": {"source": "upload", "description": "smoke visible near room entrance"},
            "location": {"floor": 2, "room": "Lab 203", "zone": "east-wing"},
            "camera": {"camera_id": "C-04", "status": "online"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["incident_context"]["incident_id"] == incident_id
    assert payload["incident_context"]["type"] == "fire"
    assert payload["incident_context"]["hazards"]
