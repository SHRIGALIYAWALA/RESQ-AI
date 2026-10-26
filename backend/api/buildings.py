import json
import re
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.database import get_db
from backend.models.building import Building, Floor, Room, Corridor, ExitPoint, Occupant, Resource, Route, Notification, SensorReading, OccupancyObservation
from backend.schemas.building import BuildingCreate
from backend.building.building_service import create_building_full
from backend.building.evacuation_graph import build_graph_from_db
from backend.building.zone_manager import DangerZoneEngine
from backend.routing.safe_path import SafePathCoordinator
from backend.services.spatial_service import spatial_service
from backend.security.dependencies import get_identity, require_operator, require_dispatcher, log_audit
from backend.api.websocket import ws_manager

router = APIRouter(prefix="/api/buildings", tags=["Buildings"])
settings = get_settings()


def get_request_tenant(request: Request) -> str:
    return str(getattr(request.state, "identity", {}).get("tenant_id", "demo"))


@router.post("")
def create_building_api(
    payload: BuildingCreate,
    request: Request,
    db: Session = Depends(get_db),
    identity: dict = Depends(require_operator),
) -> Any:
    tenant_id = get_request_tenant(request)
    building_payload = payload.model_dump()
    building = create_building_full(db, building_payload, tenant_id=tenant_id)
    log_audit(db, tenant_id, "building_created", "building", building.id, identity.get("username", "system"), {"name": building.name})

    return {
        "id": building.id,
        "name": building.name,
        "address": building.address,
        "description": building.description,
        "floors": [{"id": f.id, "number": f.number, "name": f.name} for f in building.floors],
        "rooms": [{"id": r.id, "name": r.name, "floor_number": r.floor_number, "occupancy": r.occupancy, "capacity": r.capacity} for r in building.rooms],
        "routes": [{"id": route.id, "name": route.name, "origin": route.origin, "destination": route.destination} for route in building.routes],
        "resources": [{"id": res.id, "name": res.name, "resource_type": res.resource_type, "status": res.status} for res in building.resources],
    }


@router.post("/nearby")
def find_nearby_buildings_api(payload: Dict[str, Any], request: Request, db: Session = Depends(get_db)) -> Any:
    """Find buildings within radius using PostGIS (PostgreSQL) or haversine fallback."""
    latitude = float(payload.get("latitude", 0))
    longitude = float(payload.get("longitude", 0))
    radius_m = float(payload.get("radius_m", 5000))
    tenant_id = get_request_tenant(request)
    results = spatial_service.find_nearby_buildings(db, latitude, longitude, radius_m, tenant_id=tenant_id)
    return {
        "origin": {"latitude": latitude, "longitude": longitude},
        "radius_m": radius_m,
        "count": len(results),
        "buildings": results,
    }


@router.get("")
def list_buildings_api(request: Request, db: Session = Depends(get_db)) -> Any:
    tenant_id = get_request_tenant(request)
    buildings = db.query(Building).filter(Building.tenant_id == tenant_id).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "address": b.address,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "floors_count": len(b.floors),
            "rooms_count": len(b.rooms),
            "cameras_count": len(b.cameras),
            "verification_status": b.verification_status,
        }
        for b in buildings
    ]


@router.get("/{building_id}")
def get_building_api(building_id: int, request: Request, db: Session = Depends(get_db)) -> Any:
    tenant_id = get_request_tenant(request)
    building = db.query(Building).filter(Building.id == building_id, Building.tenant_id == tenant_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    return {
        "id": building.id,
        "name": building.name,
        "address": building.address,
        "description": building.description,
        "floors": [{"id": f.id, "number": f.number, "name": f.name} for f in building.floors],
        "rooms": [{"id": r.id, "name": r.name, "floor_number": r.floor_number, "zone": r.zone, "occupancy": r.occupancy, "capacity": r.capacity} for r in building.rooms],
        "routes": [{"id": route.id, "name": route.name, "origin": route.origin, "destination": route.destination, "status": route.status, "risk": route.risk} for route in building.routes],
        "resources": [{"id": res.id, "name": res.name, "resource_type": res.resource_type, "status": res.status, "location": res.location} for res in building.resources],
    }


@router.get("/{building_id}/floors")
def get_building_floors_api(building_id: int, db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    floors = []
    for f in building.floors:
        rooms = [{"id": r.id, "name": r.name, "occupancy": r.occupancy, "capacity": r.capacity, "zone": r.zone} for r in f.rooms]
        floors.append({"id": f.id, "number": f.number, "name": f.name, "rooms": rooms})
    return {"building_id": building_id, "floors": floors}


@router.get("/{building_id}/graph")
def get_building_graph_api(building_id: int, db: Session = Depends(get_db)) -> Any:
    graph_model = build_graph_from_db(db, building_id)
    return graph_model.to_dict()


@router.post("/{building_id}/routes/evaluate")
async def evaluate_building_routes(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    graph_model = build_graph_from_db(db, building_id)
    hazards_input = payload.get("hazards", [])
    active_hazards = []
    for hz in hazards_input:
        if isinstance(hz, str):
            active_hazards.append({"type": hz, "location": "Floor 1 Corridor", "severity": "high"})
        elif isinstance(hz, dict):
            active_hazards.append(hz)

    coordinator = SafePathCoordinator()
    plan = coordinator.generate_evacuation_plan(graph_model, active_hazards)

    routes_list = []
    for room_name, r_data in plan.get("routes_by_room", {}).items():
        routes_list.append({
            "name": f"Route from {room_name} to {r_data.get('target_exit')}",
            "origin": room_name,
            "destination": r_data.get("target_exit"),
            "path": r_data.get("path", []),
            "distance_m": r_data.get("total_distance_m", 0.0),
            "safety_score": r_data.get("safety_score", 1.0),
            "status": "recommended" if r_data.get("safety_score", 1.0) > 0.5 else "caution",
            "instruction": plan.get("room_instructions", {}).get(room_name, ""),
        })

    # Broadcast update over WebSocket
    await ws_manager.broadcast({
        "event": "evacuation_routes_updated",
        "building_id": building_id,
        "active_hazards": len(active_hazards),
        "total_routes": len(routes_list),
    })

    return {
        "building_id": building_id,
        "routes": routes_list,
        "safe_exits": plan.get("safe_exits", []),
        "blocked_exits": plan.get("blocked_exits", []),
        "danger_zones": plan.get("danger_summary", {}).get("danger_zones", []),
        "human_validation_required": True,
    }


@router.post("/{building_id}/occupants")
def register_occupant(building_id: int, request: Request, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    occupant = Occupant(
        building_id=building_id,
        name=str(payload.get("name", "")).strip(),
        room_name=str(payload.get("room_name", "")).strip(),
        floor_number=int(payload.get("floor_number", 1)),
        contact_channel=str(payload.get("contact_channel", "local_display")),
        contact_value=str(payload.get("contact_value", "")),
        status=str(payload.get("status", "inside")),
    )
    db.add(occupant)
    db.commit()
    db.refresh(occupant)
    return {
        "id": occupant.id,
        "name": occupant.name,
        "room_name": occupant.room_name,
        "floor_number": occupant.floor_number,
        "status": occupant.status,
    }


@router.get("/{building_id}/occupants")
def list_occupants(building_id: int, db: Session = Depends(get_db)) -> Any:
    occupants = db.query(Occupant).filter(Occupant.building_id == building_id).all()
    return {
        "building_id": building_id,
        "occupants": [
            {
                "id": o.id,
                "name": o.name,
                "room_name": o.room_name,
                "floor_number": o.floor_number,
                "status": o.status,
                "contact_channel": o.contact_channel,
            }
            for o in occupants
        ],
    }


@router.post("/{building_id}/alert")
async def alert_building(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    message = str(payload.get("message", "Building-wide emergency alert"))
    notification = Notification(
        incident_id=0,
        recipient_type="building_occupants",
        channel="broadcast",
        address=f"building:{building_id}",
        message=message,
        status="broadcasted",
    )
    db.add(notification)
    db.commit()

    await ws_manager.broadcast({
        "event": "building_alert",
        "building_id": building_id,
        "building_name": building.name,
        "message": message,
    })

    return {
        "status": "broadcasted",
        "building_id": building_id,
        "message": message,
        "notified_count": max(len(building.rooms), 1),
    }


@router.post("/{building_id}/escalate")
async def escalate_building_emergency(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    """Escalate a room-level emergency to a building-wide alert and flag for operator review."""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    room_name = str(payload.get("room_name", "Unknown"))
    room_message = str(payload.get("room_message", "Evacuate immediately."))
    building_message = str(payload.get("building_message", "Building-wide evacuation."))

    await ws_manager.broadcast({
        "event": "emergency_escalated",
        "building_id": building_id,
        "building_name": building.name,
        "origin_room": room_name,
        "room_message": room_message,
        "building_message": building_message,
    })

    return {
        "status": "escalated",
        "building_id": building_id,
        "origin_room": room_name,
        "room_message": room_message,
        "building_message": building_message,
        "operator_review_required": True,
    }


@router.post("/{building_id}/resources/{resource_id}/reserve")
def reserve_resource(building_id: int, resource_id: int, db: Session = Depends(get_db)) -> Any:
    """Reserve a building resource (e.g. AED, first-aid kit) for an active emergency.
    Returns 409 if the resource is already reserved."""
    from backend.models.building import Resource
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.building_id == building_id,
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if resource.status == "reserved":
        raise HTTPException(status_code=409, detail="Resource already reserved by another incident.")

    resource.status = "reserved"
    db.commit()

    return {
        "id": resource.id,
        "name": resource.name,
        "resource_type": resource.resource_type,
        "status": resource.status,
        "building_id": building_id,
    }


@router.post("/{building_id}/analyze")
def analyze_building_digital_model(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    graph_model = build_graph_from_db(db, building_id)
    digital_model = {
        "building_id": building_id,
        "name": building.name,
        "source_type": payload.get("source_type", "manual"),
        "summary": payload.get("summary", ""),
        "verified": bool(payload.get("verified", False)),
        "rooms": [
            {"id": room.id, "name": room.name, "floor_number": room.floor_number, "zone": room.zone, "capacity": room.capacity}
            for room in building.rooms
        ],
        "floors": [{"id": floor.id, "number": floor.number, "name": floor.name} for floor in building.floors],
        "exits": [{"id": exit_point.id, "name": exit_point.name, "floor_number": exit_point.floor_number} for exit_point in building.exits],
        "graph": graph_model.to_dict(),
    }
    building.digital_model_status = "analyzed"
    db.commit()
    return {"building_id": building_id, "digital_model": digital_model}


@router.post("/{building_id}/verify")
def verify_building_model(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    verified = bool(payload.get("verified", False))
    building.verification_status = "verified" if verified else "unverified"
    building.verification_notes = str(payload.get("notes", ""))
    building.digital_model_status = "verified" if verified else "draft"
    db.commit()

    return {
        "building_id": building_id,
        "verification_status": building.verification_status,
        "reviewer": payload.get("reviewer", ""),
        "notes": building.verification_notes,
    }


@router.post("/{building_id}/vision")
async def ingest_building_vision(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    observations = [str(item) for item in payload.get("observations", [])]
    hazards: List[Dict[str, Any]] = []
    people_count = 0
    blocked_paths: List[str] = []

    for observation in observations:
        lower = observation.lower()
        match = re.search(r"(\d+)\s+people", lower)
        if match:
            people_count = max(people_count, int(match.group(1)))
        if "smoke" in lower:
            hazards.append({"type": "smoke", "severity": "high", "source": observation})
        if "fire" in lower:
            hazards.append({"type": "fire", "severity": "critical", "source": observation})
        if "blocked" in lower or "blockage" in lower:
            blocked_paths.append(observation)

    floor_number = int(payload.get("floor", 1))
    zone = str(payload.get("zone", ""))
    created_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    if people_count > 0:
        db.add(OccupancyObservation(
            building_id=building_id,
            floor_number=floor_number,
            zone=zone,
            people_count=people_count,
            source=str(payload.get("camera_id", "vision-ingest")),
            confidence=0.85,
            created_at=created_str,
        ))

    live_environment_state = {
        "building_id": building_id,
        "camera_id": payload.get("camera_id"),
        "floor": floor_number,
        "zone": zone,
        "people_count": people_count,
        "hazards": hazards,
        "blocked_paths": blocked_paths,
        "observations": observations,
        "updated_at": created_str,
    }
    db.commit()

    await ws_manager.broadcast({
        "event": "building_vision_update",
        "building_id": building_id,
        "live_environment_state": live_environment_state,
    })

    return {"building_id": building_id, "live_environment_state": live_environment_state}


@router.post("/{building_id}/sensor-readings")
def ingest_sensor_reading(building_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    created_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    value = payload.get("value", {})
    reading = SensorReading(
        building_id=building_id,
        sensor_type=str(payload.get("sensor_type", "generic")),
        value_json=json.dumps(value),
        source=str(payload.get("source", "api")),
        created_at=created_str,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    return {
        "id": reading.id,
        "building_id": building_id,
        "sensor_type": reading.sensor_type,
        "value": json.loads(reading.value_json or "{}"),
        "source": reading.source,
        "created_at": reading.created_at,
    }


@router.get("/{building_id}/sensor-readings")
def list_sensor_readings(building_id: int, db: Session = Depends(get_db)) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    readings = db.query(SensorReading).filter(SensorReading.building_id == building_id).order_by(SensorReading.id.desc()).all()
    return {
        "building_id": building_id,
        "readings": [
            {
                "id": reading.id,
                "sensor_type": reading.sensor_type,
                "value": json.loads(reading.value_json or "{}"),
                "source": reading.source,
                "created_at": reading.created_at,
            }
            for reading in readings
        ],
    }


@router.put("/{building_id}/location")
def set_building_location_api(
    building_id: int,
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    identity: dict = Depends(require_operator),
) -> Any:
    building = spatial_service.set_building_location(
        db, building_id, float(payload["latitude"]), float(payload["longitude"])
    )
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    tenant_id = get_request_tenant(request)
    log_audit(db, tenant_id, "building_location_set", "building", building_id, identity.get("username", "system"), payload)
    return {
        "id": building.id,
        "name": building.name,
        "latitude": building.latitude,
        "longitude": building.longitude,
    }
