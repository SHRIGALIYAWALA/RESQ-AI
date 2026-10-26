from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.building.room_graph import BuildingGraphModel
from backend.models.building import Building, Floor, Room, Corridor, Door, Staircase, ExitPoint


def build_graph_from_db(db: Session, building_id: int) -> BuildingGraphModel:
    """Constructs a topological BuildingGraphModel from SQLAlchemy relational entities."""
    building = db.query(Building).filter(Building.id == building_id).first()
    graph_model = BuildingGraphModel(building_id=building_id)

    if not building:
        return graph_model

    # 1. Add Rooms
    for room in building.rooms:
        graph_model.add_room_node(
            name=room.name,
            floor_number=room.floor_number or (room.floor.number if room.floor else 1),
            zone=room.zone or room.name,
            capacity=room.capacity or 20,
            occupancy=room.occupancy or 0,
        )

    # 2. Add Corridors
    for corridor in building.corridors:
        floor_num = corridor.floor_id or 1
        graph_model.add_corridor_node(name=corridor.name, floor_number=floor_num)

    # 3. Add Staircases
    for stair in building.staircases:
        graph_model.add_staircase_node(name=stair.name, floor_number=1, connects_floors=[1, 2, 3])

    # 4. Add Exits
    for exit_pt in building.exits:
        floor_num = exit_pt.floor_id or 1
        graph_model.add_exit_node(name=exit_pt.name, floor_number=floor_num, location=exit_pt.location or "Ground")

    # 5. Connect Doors & Hallways
    # If explicit doors exist, connect them; otherwise establish topological room-to-corridor and corridor-to-exit links
    if building.doors:
        for door in building.doors:
            # find corresponding corridor or room
            graph_model.add_connection(
                door.name,
                door.room_name or "Corridor A",
                distance_m=5.0,
                status=door.status or "available",
            )
    else:
        # Auto-connect rooms to nearby corridors and corridors to exits
        corridors = [c.name for c in building.corridors] or ["Corridor Ground", "Corridor Floor 2"]
        exits = [e.name for e in building.exits] or ["Emergency Exit A", "Main Exit"]

        for room in building.rooms:
            # Connect room to first corridor on matching floor or fallback
            target_corridor = corridors[0]
            graph_model.add_connection(room.name, target_corridor, distance_m=8.0)

        for corridor_name in corridors:
            for exit_name in exits:
                graph_model.add_connection(corridor_name, exit_name, distance_m=15.0)

    return graph_model


def build_graph_from_dict(payload: Dict[str, Any], building_id: int = 1) -> BuildingGraphModel:
    """Constructs a BuildingGraphModel from a JSON/Dict building description."""
    graph_model = BuildingGraphModel(building_id=building_id)

    rooms = payload.get("rooms", [])
    for room in rooms:
        graph_model.add_room_node(
            name=room.get("name", "Room"),
            floor_number=room.get("floor_number", 1),
            zone=room.get("zone", ""),
            capacity=room.get("capacity", 20),
            occupancy=room.get("occupancy", 0),
        )

    corridors = payload.get("corridors", [])
    if not corridors:
        corridors = [{"name": "Central Corridor", "floor_number": 1}]
    for corridor in corridors:
        graph_model.add_corridor_node(name=corridor.get("name", "Corridor"), floor_number=corridor.get("floor_number", 1))

    exits = payload.get("exits", [])
    if not exits:
        exits = [{"name": "Emergency Exit A", "floor_number": 1}]
    for ex in exits:
        graph_model.add_exit_node(name=ex.get("name", "Exit"), floor_number=ex.get("floor_number", 1), location=ex.get("location", ""))

    routes = payload.get("routes", [])
    if routes:
        for r in routes:
            graph_model.add_connection(
                r.get("origin", ""),
                r.get("destination", ""),
                distance_m=float(r.get("distance_m", 10.0)),
                status=r.get("status", "available"),
            )
    else:
        # Default fallback connections
        for room in rooms:
            graph_model.add_connection(room.get("name", ""), corridors[0].get("name", ""), distance_m=10.0)
        for corridor in corridors:
            for ex in exits:
                graph_model.add_connection(corridor.get("name", ""), ex.get("name", ""), distance_m=15.0)

    return graph_model
