from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.building import OccupancyObservation
from backend.vision.stream_manager import stream_manager
from backend.api.websocket import ws_manager

router = APIRouter(prefix="/api/vision", tags=["Vision"])


@router.get("/analytics")
def get_vision_analytics() -> Any:
    """Returns real-time aggregated vision data across all registered cameras."""
    streams = stream_manager.get_all_streams()
    total_people = sum(s.get("latest_analysis", {}).get("people_count", 0) for s in streams)
    all_hazards = []
    for s in streams:
        for hz in s.get("latest_analysis", {}).get("hazards", []):
            all_hazards.append({**hz, "camera_id": s.get("camera_id"), "zone": s.get("zone_name")})

    return {
        "cameras_active": len(streams),
        "total_people_detected": total_people,
        "active_hazards": all_hazards,
        "streams": streams,
    }


@router.post("/trigger-hazard")
async def trigger_hazard_on_camera(payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    """Manually flags or tests a hazard detection on a specific camera stream."""
    camera_id = str(payload.get("camera_id", "1"))
    hazard_type = str(payload.get("hazard_type", "fire")).lower()
    severity = str(payload.get("severity", "critical"))
    zone = str(payload.get("zone", "Room 202"))

    stream = stream_manager.get_stream(camera_id)
    if stream:
        hazard_entry = {
            "type": hazard_type,
            "severity": severity,
            "confidence": 0.95,
            "location": zone,
            "source": f"CAM-{camera_id}",
            "details": f"Hazard trigger verified for {hazard_type.upper()}.",
        }
        with stream.lock:
            stream.latest_analysis["hazards"] = [hazard_entry]

    # Broadcast event to WebSocket
    await ws_manager.broadcast({
        "event": "hazard_detected",
        "camera_id": camera_id,
        "hazard_type": hazard_type,
        "severity": severity,
        "zone": zone,
    })

    return {"status": "hazard_triggered", "camera_id": camera_id, "hazard_type": hazard_type, "zone": zone}
