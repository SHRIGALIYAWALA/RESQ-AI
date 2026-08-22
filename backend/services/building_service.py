from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.models.building import (
    AssemblyPoint,
    Building,
    Camera,
    Corridor,
    Door,
    Elevator,
    Equipment,
    ExitPoint,
    Floor,
    OutdoorArea,
    Resource,
    Room,
    Route,
    Sensor,
    Staircase,
)


def create_building(db: Session, payload: Dict[str, Any]) -> Building:
    building = Building(
        name=payload["name"],
        address=payload["address"],
        description=payload.get("description", ""),
        active=True,
        digital_model_status="draft",
        verification_status="unverified",
    )
    db.add(building)
    db.flush()

    for floor_data in payload.get("floors", []):
        floor = Floor(
            building_id=building.id,
            number=floor_data["number"],
            name=floor_data["name"],
            description=floor_data.get("description", ""),
        )
        db.add(floor)
        db.flush()

    for room_data in payload.get("rooms", []):
        floor_number = room_data["floor_number"]
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first()
        if floor is None:
            floor = Floor(building_id=building.id, number=floor_number, name=f"Floor {floor_number}")
            db.add(floor)
            db.flush()
        room = Room(
            building_id=building.id,
            floor_id=floor.id,
            name=room_data["name"],
            zone=room_data.get("zone", ""),
            occupancy=room_data.get("occupancy", 0),
            capacity=room_data.get("capacity", 0),
            notes=room_data.get("notes", ""),
            floor_number=floor_number,
        )
        db.add(room)

    for corridor_data in payload.get("corridors", []):
        floor_number = corridor_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        corridor = Corridor(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=corridor_data["name"],
            length_m=corridor_data.get("length_m", 0.0),
            status=corridor_data.get("status", "available"),
        )
        db.add(corridor)

    for door_data in payload.get("doors", []):
        floor_number = door_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        door = Door(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=door_data["name"],
            room_name=door_data.get("room_name", ""),
            status=door_data.get("status", "available"),
            accessibility=door_data.get("accessibility", "standard"),
        )
        db.add(door)

    for stair_data in payload.get("staircases", []):
        floor_number = stair_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        staircase = Staircase(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=stair_data["name"],
            status=stair_data.get("status", "available"),
            direction=stair_data.get("direction", "up"),
        )
        db.add(staircase)

    for elevator_data in payload.get("elevators", []):
        floor_number = elevator_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        elevator = Elevator(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=elevator_data["name"],
            status=elevator_data.get("status", "available"),
            accessibility=elevator_data.get("accessibility", "standard"),
        )
        db.add(elevator)

    for exit_data in payload.get("exits", []):
        floor_number = exit_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        exit_point = ExitPoint(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=exit_data["name"],
            location=exit_data.get("location", ""),
            status=exit_data.get("status", "available"),
        )
        db.add(exit_point)

    for area_data in payload.get("outdoor_areas", []):
        outdoor = OutdoorArea(
            building_id=building.id,
            name=area_data["name"],
            area_type=area_data.get("area_type", "road"),
            status=area_data.get("status", "available"),
        )
        db.add(outdoor)

    for assembly_data in payload.get("assembly_points", []):
        assembly = AssemblyPoint(
            building_id=building.id,
            name=assembly_data["name"],
            location=assembly_data.get("location", ""),
            capacity=assembly_data.get("capacity", 0),
        )
        db.add(assembly)

    for equipment_data in payload.get("equipment", []):
        floor_number = equipment_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        equipment = Equipment(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=equipment_data["name"],
            equipment_type=equipment_data["equipment_type"],
            location=equipment_data.get("location", ""),
            status=equipment_data.get("status", "available"),
            notes=equipment_data.get("notes", ""),
        )
        db.add(equipment)

    for camera_data in payload.get("cameras", []):
        floor_number = camera_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        camera = Camera(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=camera_data["name"],
            location=camera_data.get("location", ""),
            zone=camera_data.get("zone", ""),
            direction=camera_data.get("direction", ""),
            status=camera_data.get("status", "online"),
            last_update=camera_data.get("last_update", ""),
        )
        db.add(camera)

    for sensor_data in payload.get("sensors", []):
        floor_number = sensor_data.get("floor_number")
        floor = db.query(Floor).filter_by(building_id=building.id, number=floor_number).first() if floor_number is not None else None
        sensor = Sensor(
            building_id=building.id,
            floor_id=floor.id if floor else None,
            name=sensor_data["name"],
            sensor_type=sensor_data.get("sensor_type", "generic"),
            location=sensor_data.get("location", ""),
            status=sensor_data.get("status", "online"),
        )
        db.add(sensor)

    for route_data in payload.get("routes", []):
        route = Route(
            building_id=building.id,
            name=route_data["name"],
            origin=route_data["origin"],
            destination=route_data["destination"],
            distance_m=route_data.get("distance_m", 0.0),
            estimated_time_s=route_data.get("estimated_time_s", 0),
            risk=route_data.get("risk", 0.0),
            status=route_data.get("status", "available"),
            accessibility=route_data.get("accessibility", "standard"),
        )
        db.add(route)

    for resource_data in payload.get("resources", []):
        resource = Resource(
            building_id=building.id,
            name=resource_data["name"],
            resource_type=resource_data["resource_type"],
            status=resource_data.get("status", "available"),
            location=resource_data.get("location", ""),
            notes=resource_data.get("notes", ""),
        )
        db.add(resource)

    db.commit()
    db.refresh(building)
    return building


def get_building(db: Session, building_id: int) -> Building:
    return db.query(Building).filter(Building.id == building_id).first()


def get_building_summary(db: Session, building_id: int) -> Dict[str, Any]:
    building = get_building(db, building_id)
    if building is None:
        raise ValueError("Building not found")
    return {
        "id": building.id,
        "building_id": building.id,
        "name": building.name,
        "address": building.address,
        "floors": [{"id": floor.id, "name": floor.name, "number": floor.number} for floor in building.floors],
        "rooms": [{"id": room.id, "name": room.name, "floor_number": room.floor_number, "zone": room.zone, "occupancy": room.occupancy} for room in building.rooms],
        "corridors": [{"id": c.id, "name": c.name, "status": c.status} for c in building.corridors],
        "exits": [{"id": e.id, "name": e.name, "status": e.status} for e in building.exits],
        "routes": [{"id": route.id, "name": route.name, "origin": route.origin, "destination": route.destination, "status": route.status} for route in building.routes],
        "resources": [{"id": resource.id, "name": resource.name, "resource_type": resource.resource_type, "status": resource.status, "location": resource.location} for resource in building.resources],
        "equipment": [{"id": eq.id, "name": eq.name, "equipment_type": eq.equipment_type, "status": eq.status} for eq in building.equipment],
        "cameras": [{"id": c.id, "name": c.name, "location": c.location, "status": c.status} for c in building.cameras],
        "verification_status": building.verification_status,
        "digital_model_status": building.digital_model_status,
    }


def get_building_floors(db: Session, building_id: int) -> List[Dict[str, Any]]:
    floors = db.query(Floor).filter(Floor.building_id == building_id).all()
    return [{"id": f.id, "number": f.number, "name": f.name} for f in floors]
