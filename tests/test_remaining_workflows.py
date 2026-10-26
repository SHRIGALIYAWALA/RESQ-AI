from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_assignment_timeline_and_report_export():
    building = client.post(
        "/api/buildings",
        json={
            "name": "Response Hub",
            "address": "1 Safety Way",
            "floors": [{"number": 1, "name": "Ground"}],
            "resources": [{"name": "Hose A", "resource_type": "hose"}],
        },
    )
    assert building.status_code == 200, building.text
    building_body = building.json()
    building_id = building_body["id"]
    resource_id = building_body["resources"][0]["id"]

    incident = client.post(
        "/api/incidents",
        json={
            "title": "Fire alarm",
            "incident_type": "fire",
            "building_id": building_id,
            "description": "Alarm active",
            "location": {"floor": 1},
        },
    )
    assert incident.status_code == 200, incident.text
    incident_id = incident.json()["id"]

    assignment = client.post(
        f"/api/incidents/{incident_id}/resource-assignments",
        json={"resource_id": resource_id},
    )
    assert assignment.status_code == 200, assignment.text
    assert assignment.json()["status"] == "assigned"

    timeline = client.get(f"/api/incidents/{incident_id}/timeline")
    assert timeline.status_code == 200
    assert {event["type"] for event in timeline.json()} >= {"incident_created", "resource_assigned"}

    report = client.post(f"/api/incidents/{incident_id}/reports")
    assert report.status_code == 200, report.text
    report_id = report.json()["id"]

    exported = client.get(f"/api/incidents/{incident_id}/reports/{report_id}/export")
    assert exported.status_code == 200
    assert "Incident report: Fire alarm" in exported.text

    exported_pdf = client.get(f"/api/incidents/{incident_id}/reports/{report_id}/export.pdf")
    assert exported_pdf.status_code == 200
    assert exported_pdf.content.startswith(b"%PDF-1.4")

    tools = client.post(f"/api/incidents/{incident_id}/tools/validate", json={"tools": ["triage_model", "unknown_tool"]})
    assert tools.status_code == 200
    assert tools.json()["all_available"] is False


def test_readiness_and_sensor_reading_ingestion():
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["database"] == "ok"

    building = client.post(
        "/api/buildings",
        json={"name": "Sensor Building", "address": "2 Signal Street", "floors": [{"number": 1, "name": "Ground"}]},
    )
    assert building.status_code == 200, building.text
    building_id = building.json()["id"]

    reading = client.post(
        f"/api/buildings/{building_id}/sensor-readings",
        json={"sensor_type": "smoke", "value": {"ppm": 12}, "source": "sensor-gateway"},
    )
    assert reading.status_code == 200, reading.text
    assert reading.json()["value"]["ppm"] == 12

    readings = client.get(f"/api/buildings/{building_id}/sensor-readings")
    assert readings.status_code == 200
    assert len(readings.json()["readings"]) >= 1
