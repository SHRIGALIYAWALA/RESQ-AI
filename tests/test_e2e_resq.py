from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_full_mvp_emergency_flow():
    # 1. Register Building Digital Twin
    b_res = client.post(
        "/api/buildings",
        json={
            "name": "Global Tech Center",
            "address": "400 Enterprise Boulevard",
            "floors": [{"number": 1, "name": "Ground Floor"}, {"number": 2, "name": "Second Floor"}],
            "rooms": [
                {"name": "Room 101", "floor_number": 1, "capacity": 20, "occupancy": 5},
                {"name": "Room 201", "floor_number": 2, "capacity": 20, "occupancy": 8},
                {"name": "Room 202", "floor_number": 2, "capacity": 25, "occupancy": 14},
            ],
            "exits": [
                {"name": "Exit North", "floor_number": 1, "location": "North Wing"},
                {"name": "Exit South", "floor_number": 1, "location": "South Wing"},
            ],
            "resources": [{"name": "AED 1", "resource_type": "aed", "location": "Lobby"}],
        },
    )
    assert b_res.status_code == 200, b_res.text
    building_id = b_res.json()["id"]

    # 2. Register Live Camera
    cam_res = client.post(
        "/api/cameras",
        json={
            "building_id": building_id,
            "name": "CAM-F2-01",
            "source": "0",
            "zone": "Room 202",
            "floor_number": 2,
        },
    )
    assert cam_res.status_code == 200, cam_res.text
    camera_id = cam_res.json()["id"]

    # 3. Trigger Hazard on Camera
    hz_res = client.post(
        "/api/vision/trigger-hazard",
        json={
            "camera_id": str(camera_id),
            "hazard_type": "fire",
            "severity": "critical",
            "zone": "Room 202",
        },
    )
    assert hz_res.status_code == 200

    # 4. Report Emergency Incident
    inc_res = client.post(
        "/api/incidents",
        json={
            "title": "Severe Fire in Room 202",
            "incident_type": "fire",
            "building_id": building_id,
            "severity": "critical",
            "location": {"floor": 2, "room": "Room 202"},
            "description": "Flames detected by optical sensors and occupants running toward exits.",
        },
    )
    assert inc_res.status_code == 200, inc_res.text
    incident_data = inc_res.json()
    incident_id = incident_data["id"]

    # Verify Multi-Agent Analysis
    analysis = incident_data.get("analysis", {})
    assert analysis.get("status") == "analysis_complete"
    assert "evacuation_plan" in analysis
    assert len(analysis["evacuation_plan"]["room_instructions"]) > 0

    # 5. Evaluate Evacuation Plan
    evac_res = client.get(f"/api/evacuation/plan/{building_id}")
    assert evac_res.status_code == 200
    evac_data = evac_res.json()
    assert "safe_exits" in evac_data

    # 6. Generate & Authorize Voice Announcement
    comms = analysis.get("communications", {})
    ann_res = client.post(
        "/api/announcements/generate",
        json={
            "building_id": building_id,
            "text_en": comms.get("announcement_script_en", "Evacuate immediately."),
            "text_hi": comms.get("announcement_script_hi", "तुरंत बाहर निकलें।"),
            "text_gu": comms.get("announcement_script_gu", "તરત જ બહાર નીકળો."),
        },
    )
    assert ann_res.status_code == 200
    ann_id = ann_res.json()["id"]

    appr_res = client.post(f"/api/announcements/{ann_id}/approve", json={"operator": "Commander"})
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "broadcast_released"
