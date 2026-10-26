from typing import Any, Dict, List, Optional

from backend.building.room_graph import BuildingGraphModel
from backend.building.zone_manager import DangerZoneEngine
from backend.routing.indoor_routing import IndoorRouteEngine


class SafePathCoordinator:
    """Combines building graph, active hazard risk engine, and indoor routing to produce
    comprehensive evacuation plans and room-specific actionable instructions.
    """

    def __init__(self):
        self.danger_engine = DangerZoneEngine()
        self.route_engine = IndoorRouteEngine()

    def generate_evacuation_plan(
        self,
        graph_model: BuildingGraphModel,
        active_hazards: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # 1. Update multi-hop danger scores across the building graph
        zone_summary = self.danger_engine.update_risk_scores(graph_model, active_hazards)

        # 2. Extract all room nodes
        g = graph_model.graph
        room_nodes = [n for n, d in g.nodes(data=True) if d.get("node_type") == "room"]
        exits = graph_model.get_exits()

        routes_by_room: Dict[str, Any] = {}
        room_instructions: Dict[str, str] = {}
        blocked_exits = []
        safe_exits = []

        # Categorize exits
        for ex in exits:
            ex_risk = g.nodes[ex].get("risk_score", 0.0)
            if ex_risk >= 0.70:
                blocked_exits.append(ex)
            else:
                safe_exits.append(ex)

        if not safe_exits and exits:
            # Fallback to least dangerous exit if all have non-zero risk
            safe_exits = [min(exits, key=lambda e: g.nodes[e].get("risk_score", 1.0))]

        # 3. Compute optimal safe route for each room
        for room in room_nodes:
            route = self.route_engine.calculate_safest_route(graph_model, origin_room=room, target_exits=safe_exits)
            if route:
                routes_by_room[room] = route
                target_exit = route["target_exit"]
                path_str = " -> ".join(route["path"])
                
                # Check if high hazard nearby
                room_risk = g.nodes[room].get("risk_score", 0.0)
                if room_risk >= 0.8:
                    instruction = f"CRITICAL: Immediate evacuation required! Exit via {target_exit} immediately following path: {path_str}."
                elif room_risk >= 0.5:
                    instruction = f"WARNING: Elevated risk nearby. Proceed calmly along path {path_str} toward {target_exit}."
                else:
                    instruction = f"Proceed toward {target_exit} via {path_str}. Maintain orderly movement."

                room_instructions[room] = instruction
            else:
                room_instructions[room] = f"Shelter in place if path blocked. Await emergency responder guidance."

        return {
            "building_id": graph_model.building_id,
            "danger_summary": zone_summary,
            "safe_exits": safe_exits,
            "blocked_exits": blocked_exits,
            "routes_by_room": routes_by_room,
            "room_instructions": room_instructions,
            "total_rooms_routed": len(routes_by_room),
        }
