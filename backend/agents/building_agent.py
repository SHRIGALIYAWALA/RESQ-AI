from typing import Any, Dict, List, Optional
from backend.building.room_graph import BuildingGraphModel


class BuildingAgent:
    """Specialized agent responsible for monitoring building digital twin integrity, sensor telemetry, and structure graphs."""

    name = "BUILDING_AGENT"

    def assess_building(self, graph_model: BuildingGraphModel) -> Dict[str, Any]:
        g = graph_model.graph
        nodes = list(g.nodes(data=True))
        edges = list(g.edges(data=True))

        room_count = sum(1 for n, d in nodes if d.get("node_type") == "room")
        corridor_count = sum(1 for n, d in nodes if d.get("node_type") == "corridor")
        exit_count = sum(1 for n, d in nodes if d.get("node_type") == "exit")
        blocked_edges = sum(1 for u, v, d in edges if d.get("hazard_blocked", False) or d.get("status") == "blocked")

        return {
            "agent": self.name,
            "status": "completed",
            "building_id": graph_model.building_id,
            "total_nodes": len(nodes),
            "rooms": room_count,
            "corridors": corridor_count,
            "exits": exit_count,
            "active_connections": len(edges) - blocked_edges,
            "blocked_corridors": blocked_edges,
            "graph_connectivity": "intact" if exit_count > 0 and len(edges) > 0 else "degraded",
        }
