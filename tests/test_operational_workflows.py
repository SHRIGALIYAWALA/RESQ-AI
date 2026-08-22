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
