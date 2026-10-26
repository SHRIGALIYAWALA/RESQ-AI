"""Tests for knowledge base and spatial APIs."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_knowledge_query_returns_grounded_sops():
    response = client.post("/api/knowledge/query", json={
        "incident_type": "fire",
        "query": "evacuation stairwell smoke",
        "top_k": 2,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["grounded"] is True
    assert len(data["results"]) >= 1
    assert data["results"][0].get("hazard_type") == "fire" or "fire" in data["results"][0].get("title", "").lower()


def test_knowledge_list_sops():
    response = client.get("/api/knowledge/sops")
    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_nearby_buildings_haversine():
    building = client.post("/api/buildings", json={
        "name": "Geo Tower",
        "address": "1 Map Street",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "floors": [{"number": 1, "name": "Ground"}],
        "rooms": [{"name": "Lobby", "floor_number": 1}],
    })
    assert building.status_code == 200, building.text

    nearby = client.post("/api/buildings/nearby", json={
        "latitude": 28.6140,
        "longitude": 77.2091,
        "radius_m": 5000,
    })
    assert nearby.status_code == 200, nearby.text
    data = nearby.json()
    assert data["count"] >= 1
    assert data["buildings"][0]["distance_m"] < 5000


def test_set_building_location():
    building = client.post("/api/buildings", json={
        "name": "Loc Building",
        "address": "2 GPS Road",
        "floors": [{"number": 1, "name": "Ground"}],
    })
    building_id = building.json()["id"]

    loc = client.put(f"/api/buildings/{building_id}/location", json={
        "latitude": 19.0760,
        "longitude": 72.8777,
    })
    assert loc.status_code == 200, loc.text
    assert loc.json()["latitude"] == 19.0760


def test_audit_log_accessible_in_demo():
    response = client.get("/api/audit")
    assert response.status_code == 200
    assert "events" in response.json()
