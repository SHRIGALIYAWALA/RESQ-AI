from typing import Any, Dict, List, Optional

from backend.building.room_graph import BuildingGraphModel
from backend.routing.safe_path import SafePathCoordinator


class EvacuationAgent:
    """Specialized agent responsible for calculating optimal evacuation routes and room-specific instructions."""

    name = "EVACUATION_AGENT"

    def __init__(self):
        self.coordinator = SafePathCoordinator()

    def generate_plan(
        self,
        graph_model: BuildingGraphModel,
        active_hazards: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        plan = self.coordinator.generate_evacuation_plan(graph_model, active_hazards)

        return {
            "agent": self.name,
            "status": "completed",
            "evacuation_active": len(active_hazards) > 0,
            "primary_safe_exits": plan.get("safe_exits", []),
            "blocked_exits": plan.get("blocked_exits", []),
            "danger_zones": plan.get("danger_summary", {}).get("danger_zones", []),
            "safe_zones": plan.get("danger_summary", {}).get("safe_zones", []),
            "room_instructions": plan.get("room_instructions", {}),
            "routes_by_room": plan.get("routes_by_room", {}),
            "algorithm_used": "Weighted Dijkstra / A* Safe Path Formulation",
        }
