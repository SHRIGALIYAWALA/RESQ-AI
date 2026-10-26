from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_graph_route_evaluation_and_resource_reservation():
    response = client.post(
        "/api/buildings",
        json={
            "name": "Operations Center",
            "address": "9 Response Road",
            "floors": [{"number": 1, "name": "Ground"}],
            "rooms": [{"name": "Control", "floor_number": 1}],
            "routes": [
                {"name": "Safe Exit", "origin": "Control", "destination": "Exit A", "risk": 0.1},
                {"name": "Smoke Route", "origin": "Control", "destination": "Exit B", "risk": 0.8},
            ],
            "resources": [{"name": "AED 1", "resource_type": "aed"}],
        },
    )
    assert response.status_code == 200, response.text
    building_id = response.json()["id"]

    graph = client.get(f"/api/buildings/{building_id}/graph")
    assert graph.status_code == 200
    assert any(node["type"] == "room" for node in graph.json()["nodes"])
    assert len(graph.json()["edges"]) >= 3

    routes = client.post(
        f"/api/buildings/{building_id}/routes/evaluate",
        json={"hazards": ["fire"]},
    )
    assert routes.status_code == 200
    assert routes.json()["routes"][0]["status"] == "recommended"
    assert routes.json()["human_validation_required"] is True

    resource_id = response.json()["resources"][0]["id"]
    reserved = client.post(f"/api/buildings/{building_id}/resources/{resource_id}/reserve")
    assert reserved.status_code == 200
    assert reserved.json()["status"] == "reserved"

    conflict = client.post(f"/api/buildings/{building_id}/resources/{resource_id}/reserve")
    assert conflict.status_code == 409


def test_preincident_room_occupants_and_incident_notifications():
    building = client.post(
        "/api/buildings",
        json={
            "name": "Occupied Tower",
            "address": "88 Occupant Avenue",
            "floors": [{"number": 2, "name": "Second Floor"}],
            "rooms": [{"name": "Room 204", "floor_number": 2, "capacity": 3, "occupancy": 2}],
        },
    )
    assert building.status_code == 200, building.text
    building_id = building.json()["id"]

    occupant = client.post(
        f"/api/buildings/{building_id}/occupants",
        json={
            "name": "Alice Chen",
            "room_name": "Room 204",
            "floor_number": 2,
            "contact_channel": "local_display",
            "contact_value": "Room 204 display",
            "status": "inside",
        },
    )
    assert occupant.status_code == 200, occupant.text
    assert occupant.json()["name"] == "Alice Chen"

    occupants = client.get(f"/api/buildings/{building_id}/occupants")
    assert occupants.status_code == 200
    assert any(item["room_name"] == "Room 204" for item in occupants.json()["occupants"])

    incident = client.post(
        "/api/incidents",
        json={
            "title": "Fire alarm on second floor",
            "incident_type": "fire",
            "building_id": building_id,
            "description": "Smoke reported near Room 204",
            "location": {"floor": 2, "room": "Room 204"},
            "severity": "high",
        },
    )
    assert incident.status_code == 200, incident.text
    incident_id = incident.json()["id"]

    alerts = client.post(f"/api/incidents/{incident_id}/notify-occupants", json={"message": "Evacuate immediately via nearest safe exit."})
    assert alerts.status_code == 200, alerts.text
    assert alerts.json()["notified_count"] >= 1
    assert any(item["room_name"] == "Room 204" for item in alerts.json()["notifications"])

    building_alert = client.post(f"/api/buildings/{building_id}/alert", json={"message": "Building-wide evacuation."})
    assert building_alert.status_code == 200, building_alert.text
    assert building_alert.json()["notified_count"] >= 1

    escalation = client.post(f"/api/buildings/{building_id}/escalate", json={"room_name": "Room 204", "room_message": "Evacuate immediately.", "building_message": "Building-wide evacuation."})
    assert escalation.status_code == 200, escalation.text
    assert escalation.json()["status"] == "escalated"
    assert escalation.json()["operator_review_required"] is True

    draft = client.post(f"/api/incidents/{incident_id}/notifications", json={"message": "Responder review required."})
    assert draft.status_code == 200, draft.text
    assert draft.json()["status"] == "draft"
    notification_id = draft.json()["id"]
    blocked = client.post(f"/api/incidents/{incident_id}/notifications/{notification_id}/deliver", json={})
    assert blocked.status_code == 409
    delivered = client.post(f"/api/incidents/{incident_id}/notifications/{notification_id}/deliver", json={"approved": True})
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["status"] == "queued_local"


def test_fire_medical_and_evacuation_scenarios_are_recorded():
    building = client.post(
        "/api/buildings",
        json={
            "name": "Scenario Building",
            "address": "12 Validation Street",
            "floors": [{"number": 1, "name": "Ground"}],
            "rooms": [{"name": "Clinic", "floor_number": 1}],
        },
    )
    assert building.status_code == 200, building.text
    building_id = building.json()["id"]

    for incident_type, title in (("fire", "Smoke in corridor"), ("medical", "Medical emergency"), ("evacuation", "Evacuation drill")):
        incident = client.post(
            "/api/incidents",
            json={
                "title": title,
                "incident_type": incident_type,
                "building_id": building_id,
                "description": f"Scenario validation for {incident_type}",
                "location": {"floor": 1, "room": "Clinic"},
                "severity": "high" if incident_type != "medical" else "medium",
            },
        )
        assert incident.status_code == 200, incident.text
        body = incident.json()
        assert body["incident_type"] == incident_type
        assert body["building_id"] == building_id
