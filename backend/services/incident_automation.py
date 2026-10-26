"""Automated emergency incident pipeline.

Wires confirmed vision-pipeline hazards into the rest of the RESQ-AI workflow
without any human typing a report first:

    hazard confirmed (vision_agent + hazard_detector, temporally validated)
            -> Incident + IncidentEvent + AuditEvent persisted
            -> building graph rebuilt from verified DB structure
            -> DangerZoneEngine propagates risk across rooms/corridors/exits
            -> SafePathCoordinator recalculates safe routes + room instructions
            -> draft Notification / announcement created (PENDING_OPERATOR_APPROVAL)
            -> WebSocket broadcast to the live command center

No announcement is ever auto-approved here: this module only ever produces
`status="draft"` / `PENDING_OPERATOR_APPROVAL` records. A human operator must
call the existing approval endpoints before anything is actually delivered.

Occupancy telemetry is also persisted here so room occupancy in the digital
twin reflects live camera counts instead of only manual data entry.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from backend.database.database import SessionLocal
from backend.models.building import (
    AuditEvent,
    Building,
    Camera,
    Incident,
    IncidentEvent,
    Notification,
    OccupancyObservation,
    Room,
    Route,
)
from backend.building.evacuation_graph import build_graph_from_db
from backend.routing.safe_path import SafePathCoordinator
from backend.vision.stream_manager import stream_manager

logger = logging.getLogger("resq_ai.services.incident_automation")

coordinator = SafePathCoordinator()

# camera_id -> building_id cache to avoid a DB hit on every telemetry tick
_camera_building_cache: Dict[str, Optional[int]] = {}
# f"{building_id}:{hazard_type}" -> last auto-incident creation timestamp
_last_incident_for_hazard: Dict[str, float] = {}
INCIDENT_DEDUP_SECONDS = 120.0


def _utc_now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def _resolve_building_id(camera_id: str) -> Optional[int]:
    if camera_id in _camera_building_cache:
        return _camera_building_cache[camera_id]
    db = SessionLocal()
    try:
        cam = db.query(Camera).filter(Camera.id == int(camera_id)).first() if camera_id.isdigit() else None
        building_id = cam.building_id if cam else None
        _camera_building_cache[camera_id] = building_id
        return building_id
    except Exception:
        return None
    finally:
        db.close()


def invalidate_camera_cache(camera_id: Optional[str] = None) -> None:
    """Call after (re)registering a camera so building mapping is re-resolved."""
    if camera_id is None:
        _camera_building_cache.clear()
    else:
        _camera_building_cache.pop(str(camera_id), None)


async def handle_vision_event(event: Dict[str, Any], broadcast) -> None:
    """Entry point invoked for every vision telemetry event on the asyncio loop.

    `broadcast` is an async callable(dict) used to push additional automation
    events (incident creation, draft announcements) to connected dashboards.
    Blocking DB/graph work is dispatched to a worker thread so the event loop
    (and therefore the WebSocket broadcaster) never stalls.
    """
    event_type = event.get("event")
    try:
        if event_type == "occupancy_update":
            await asyncio.to_thread(_persist_occupancy, event)
        elif event_type == "hazard_detected":
            await _process_hazard(event, broadcast)
    except Exception as exc:
        logger.warning(f"Vision event automation failed for {event_type}: {exc}")


def _persist_occupancy(event: Dict[str, Any]) -> None:
    camera_id = str(event.get("camera_id", ""))
    building_id = _resolve_building_id(camera_id)
    if not building_id:
        return
    zone = str(event.get("zone", ""))
    floor_number = int(event.get("floor_number", 1) or 1)
    people_count = int(event.get("people_count", 0) or 0)

    db = SessionLocal()
    try:
        db.add(OccupancyObservation(
            building_id=building_id,
            floor_number=floor_number,
            zone=zone,
            people_count=people_count,
            source=f"camera:{camera_id}",
            confidence=0.75,
            created_at=_utc_now(),
        ))

        # Best-effort match of the camera's zone to a configured room so the
        # digital twin occupancy reflects live counts.
        rooms = db.query(Room).filter(Room.building_id == building_id).all()
        for room in rooms:
            room_zone = (room.zone or "").lower()
            room_name = (room.name or "").lower()
            if zone and (room_zone == zone.lower() or room_name == zone.lower()):
                room.occupancy = people_count
        db.commit()
    except Exception as exc:
        logger.debug(f"Occupancy persistence failed: {exc}")
        db.rollback()
    finally:
        db.close()


async def _process_hazard(event: Dict[str, Any], broadcast) -> None:
    camera_id = str(event.get("camera_id", ""))
    building_id = _resolve_building_id(camera_id)
    if not building_id:
        logger.debug(f"Hazard on camera {camera_id} ignored: camera not mapped to a building")
        return

    hazard_type = str(event.get("hazard_type", "unknown"))
    dedup_key = f"{building_id}:{hazard_type}"
    now = time.time()
    last = _last_incident_for_hazard.get(dedup_key, 0.0)
    if (now - last) < INCIDENT_DEDUP_SECONDS:
        # An open incident for this hazard/building almost certainly already
        # exists; avoid flooding the command center with duplicate incidents.
        return
    _last_incident_for_hazard[dedup_key] = now

    result = await asyncio.to_thread(_create_incident_and_plan, building_id, camera_id, event)
    if result is None:
        return

    await broadcast({
        "event": "auto_incident_created",
        **result,
    })


def _create_incident_and_plan(building_id: int, camera_id: str, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    hazard_type = str(event.get("hazard_type", "unknown"))
    severity = str(event.get("severity", "high"))
    zone = str(event.get("zone") or event.get("location") or "Unknown Zone")
    confidence = float(event.get("confidence", 0.0) or 0.0)
    floor_number = int(event.get("floor_number", 1) or 1)

    db = SessionLocal()
    try:
        building = db.query(Building).filter(Building.id == building_id).first()
        if not building:
            return None

        created_str = _utc_now()
        incident = Incident(
            tenant_id=building.tenant_id,
            building_id=building_id,
            title=f"Auto-detected {hazard_type.replace('_', ' ').title()} — {zone}",
            incident_type=hazard_type,
            description=(
                f"Confirmed by live vision pipeline on camera {camera_id} "
                f"with confidence {confidence:.2f}. {event.get('details', '')}"
            ).strip(),
            status="open",
            severity=severity,
            location_json=json.dumps({"zone": zone, "floor_number": floor_number, "camera_id": camera_id}),
            summary=f"Automated detection: {hazard_type} in {zone} (Floor {floor_number})",
            analysis_json="{}",
            created_at=created_str,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return _finish_incident_pipeline(db, building, incident, camera_id, zone, floor_number, hazard_type, severity, confidence, created_str)
    except Exception as exc:
        logger.warning(f"Automated incident pipeline failed: {exc}")
        db.rollback()
        return None
    finally:
        db.close()
