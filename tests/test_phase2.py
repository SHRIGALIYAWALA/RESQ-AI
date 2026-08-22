from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_building_registration_and_digital_model():
    building = client.post(
        "/api/buildings",
        json={
            "name": "North Tower",
            "address": "10 Civic Plaza",
            "description": "Campus administration building",
            "floors": [{"number": 1, "name": "Ground Floor"}, {"number": 2, "name": "Second Floor"}],
            "rooms": [
                {"name": "Lobby", "floor_number": 1, "zone": "entry", "capacity": 40},
                {"name": "Control Room", "floor_number": 2, "zone": "operations", "capacity": 12},
            ],
            "routes": [{"name": "Route 1", "origin": "Lobby", "destination": "Exit 01", "status": "available"}],
            "resources": [{"name": "Hydrant A", "resource_type": "hydrant", "location": "Front side"}],
        },
    )
    assert building.status_code == 200, building.text
    building_id = building.json()["id"]

    analysis = client.post(
        f"/api/buildings/{building_id}/analyze",
        json={
            "source_type": "floor_plan",
            "summary": "AI extracted floor, room, exit, and equipment data from uploaded files.",
            "verified": False,
        },
    )
    assert analysis.status_code == 200, analysis.text
    result = analysis.json()
    assert result["digital_model"]["building_id"] == building_id
    assert "rooms" in result["digital_model"]

    verify = client.post(
        f"/api/buildings/{building_id}/verify",
        json={"verified": True, "reviewer": "admin@demo.local", "notes": "Reviewed by administrator"},
    )
    assert verify.status_code == 200, verify.text
    payload = verify.json()
    assert payload["verification_status"] == "verified"
