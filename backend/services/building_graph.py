from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.models.building import Building


def build_building_graph(db: Session, building_id: int) -> Dict[str, Any]:
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise ValueError("Building not found")

    nodes = []
    edges = []
    for floor in building.floors:
        nodes.append({"id": f"floor:{floor.id}", "type": "floor", "name": floor.name})
    for room in building.rooms:
        nodes.append({"id": f"room:{room.id}", "type": "room", "name": room.name, "floor_number": room.floor_number})
        edges.append({"from": f"floor:{room.floor_id}", "to": f"room:{room.id}", "type": "contains"})
    for corridor in building.corridors:
        nodes.append({"id": f"corridor:{corridor.id}", "type": "corridor", "name": corridor.name, "status": corridor.status})
    for door in building.doors:
        nodes.append({"id": f"door:{door.id}", "type": "door", "name": door.name, "status": door.status})
    for staircase in building.staircases:
        nodes.append({"id": f"staircase:{staircase.id}", "type": "staircase", "name": staircase.name, "status": staircase.status})
    for elevator in building.elevators:
        nodes.append({"id": f"elevator:{elevator.id}", "type": "elevator", "name": elevator.name, "status": elevator.status})
    for exit_point in building.exits:
        nodes.append({"id": f"exit:{exit_point.id}", "type": "exit", "name": exit_point.name, "status": exit_point.status})
    for area in building.outdoor_areas:
        nodes.append({"id": f"outdoor:{area.id}", "type": "outdoor_area", "name": area.name, "status": area.status})
    for assembly in building.assembly_points:
        nodes.append({"id": f"assembly:{assembly.id}", "type": "assembly_point", "name": assembly.name})

    for route in building.routes:
        edges.append({
            "from": route.origin,
            "to": route.destination,
            "type": "route",
            "route_id": route.id,
            "status": route.status,
            "risk": route.risk,
        })
    return {"building_id": building_id, "nodes": nodes, "edges": edges}


def evaluate_routes(db: Session, building_id: int, hazard_types: list[str], max_risk: float = 1.0) -> Dict[str, Any]:
    building = db.query(Building).filter(Building.id == building_id).first()
    if building is None:
        raise ValueError("Building not found")

    hazard_set = {item.lower() for item in hazard_types}
    evaluated = []
    for route in building.routes:
        blocked = route.status != "available" or route.risk > max_risk
        reason = "available"
        if route.status != "available":
            reason = f"route status is {route.status}"
        elif route.risk > max_risk:
            reason = "route risk exceeds requested maximum"
        elif "fire" in hazard_set and route.risk >= 0.5:
            blocked = True
            reason = "risk is elevated for a fire hazard"
        evaluated.append({
            "id": route.id,
            "name": route.name,
            "origin": route.origin,
            "destination": route.destination,
            "risk": route.risk,
            "status": "blocked" if blocked else "recommended",
            "reason": reason,
        })
    return {
        "building_id": building_id,
        "hazards_considered": sorted(hazard_set),
        "routes": sorted(evaluated, key=lambda item: (item["status"] != "recommended", item["risk"])),
        "human_validation_required": True,
    }
