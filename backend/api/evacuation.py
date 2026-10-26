from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.building import Building
from backend.building.evacuation_graph import build_graph_from_db
from backend.routing.safe_path import SafePathCoordinator
from backend.vision.stream_manager import stream_manager
from backend.security.dependencies import require_responder

router = APIRouter(prefix="/api/evacuation", tags=["Evacuation"])
coordinator = SafePathCoordinator()


@router.get("/plan/{building_id}")
def get_evacuation_plan_api(
    building_id: int,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_responder),
) -> Any:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    graph_model = build_graph_from_db(db, building_id)

    # Gather live hazards from stream manager
    active_hazards = []
    for s in stream_manager.get_all_streams():
        for hz in s.get("latest_analysis", {}).get("hazards", []):
            active_hazards.append(hz)

    plan = coordinator.generate_evacuation_plan(graph_model, active_hazards)
    return plan


@router.get("/room-instruction/{building_id}/{room_name}")
def get_single_room_instruction(building_id: int, room_name: str, db: Session = Depends(get_db)) -> Any:
    graph_model = build_graph_from_db(db, building_id)
    active_hazards = []
    for s in stream_manager.get_all_streams():
        for hz in s.get("latest_analysis", {}).get("hazards", []):
            active_hazards.append(hz)

    plan = coordinator.generate_evacuation_plan(graph_model, active_hazards)
    instructions = plan.get("room_instructions", {})
    routes = plan.get("routes_by_room", {})

    instruction = instructions.get(room_name, f"Proceed calmly toward nearest emergency exit.")
    route_info = routes.get(room_name, {})

    return {
        "building_id": building_id,
        "room_name": room_name,
        "instruction": instruction,
        "recommended_exit": route_info.get("target_exit", "Emergency Exit A"),
        "route_path": route_info.get("path", []),
        "safety_score": route_info.get("safety_score", 1.0),
    }
