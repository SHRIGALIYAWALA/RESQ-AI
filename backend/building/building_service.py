import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models.building import (
    Building, Floor, Room, Corridor, Door, Staircase, Elevator, ExitPoint,
    OutdoorArea, AssemblyPoint, Equipment, Camera, Sensor, Route, Resource
)

logger = logging.getLogger("resq_ai.building.service")


def create_building_full(db: Session, payload: Dict[str, Any], tenant_id: str = "demo") -> Building:
    """Creates a comprehensive building digital twin with floors, rooms, exits, cameras, resources."""
    building = Building(
        tenant_id=tenant_id,
        name=str(payload.get("name", "Unnamed Facility")).strip(),
        address=str(payload.get("address", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        digital_model_status="active",
        verification_status="verified",
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
    )
    db.add(building)
    db.flush()

    floor_map: Dict[int, Floor] = {}
    floors_data = payload.get("floors", [])
    if not floors_data:
        floors_data = [{"number": 1, "name": "Ground Floor"}]

    for f in floors_data:
        floor_num = int(f.get("number", 1))
        floor = Floor(building_id=building.id, number=floor_num, name=str(f.get("name", f"Floor {floor_num}")))
        db.add(floor)
        db.flush()
        floor_map[floor_num] = floor

    # Rooms
    for r in payload.get("rooms", []):
        f_num = int(r.get("floor_number", 1))
        target_floor = floor_map.get(f_num, list(floor_map.values())[0])
        room = Room(
            building_id=building.id,
            floor_id=target_floor.id,
            floor_number=f_num,
            name=str(r.get("name", "Room")).strip(),
            zone=str(r.get("zone", r.get("name", ""))).strip(),
            capacity=int(r.get("capacity", 25)),
            occupancy=int(r.get("occupancy", 0)),
        )
        db.add(room)

    # Corridors
    for c in payload.get("corridors", []):
        f_num = int(c.get("floor_number", 1))
        target_floor = floor_map.get(f_num, list(floor_map.values())[0])
        corridor = Corridor(
            building_id=building.id,
            floor_id=target_floor.id,
            name=str(c.get("name", "Corridor")).strip(),
            length_m=float(c.get("length_m", 20.0)),
            status=str(c.get("status", "available")),
        )
        db.add(corridor)

    # Exits
    for e in payload.get("exits", []):
        f_num = int(e.get("floor_number", 1))
        target_floor = floor_map.get(f_num, list(floor_map.values())[0])
        exit_pt = ExitPoint(
            building_id=building.id,
            floor_id=target_floor.id,
            name=str(e.get("name", "Emergency Exit")).strip(),
            location=str(e.get("location", "Ground Level")),
            status=str(e.get("status", "available")),
        )
        db.add(exit_pt)

    # Cameras
    for cam in payload.get("cameras", []):
        f_num = int(cam.get("floor_number", 1))
        target_floor = floor_map.get(f_num, list(floor_map.values())[0])
        camera = Camera(
            building_id=building.id,
            floor_id=target_floor.id,
            name=str(cam.get("name", "CAM-01")).strip(),
            location=str(cam.get("location", "Main Hall")),
            zone=str(cam.get("zone", "Zone 1")),
            direction=str(cam.get("direction", "North")),
            status="online",
        )
        db.add(camera)

    # Resources / Equipment
    for res in payload.get("resources", []) + payload.get("equipment", []):
        resource = Resource(
            building_id=building.id,
            name=str(res.get("name", "Resource")).strip(),
            resource_type=str(res.get("resource_type", res.get("equipment_type", "general"))).strip(),
            location=str(res.get("location", "Main Corridor")),
            status=str(res.get("status", "available")),
        )
        db.add(resource)

    # Routes
    for route in payload.get("routes", []):
        r_entry = Route(
            building_id=building.id,
            name=str(route.get("name", "Evacuation Route")).strip(),
            origin=str(route.get("origin", "")).strip(),
            destination=str(route.get("destination", "")).strip(),
            distance_m=float(route.get("distance_m", 15.0)),
            risk=float(route.get("risk", 0.0)),
            status=str(route.get("status", "available")),
        )
        db.add(r_entry)

    db.commit()
    db.refresh(building)
    return building
