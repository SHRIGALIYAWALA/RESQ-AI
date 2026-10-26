import collections
import logging
from typing import Any, Dict, List, Optional
import networkx as nx

from backend.building.room_graph import BuildingGraphModel

logger = logging.getLogger("resq_ai.building.zone")


class DangerZoneEngine:
    """Calculates and dynamically propagates risk scores across the building graph.
    
    Risk Levels:
    - SAFE: 0.00 - 0.25 (Normal operation, clear transit)
    - CAUTION: 0.26 - 0.50 (Heightened awareness, prepare for instruction)
    - DANGEROUS: 0.51 - 0.80 (Active smoke/proximity risk, avoid transit)
    - CRITICAL: 0.81 - 1.00 (Direct hazard location, immediate evacuation)
    """

    HAZARD_SEVERITY_WEIGHTS = {
        "fire": 0.95,
        "explosion": 1.00,
        "smoke": 0.80,
        "hazmat": 0.90,
        "blocked_path": 0.65,
        "water": 0.45,
        "crowd_congestion": 0.50,
        "general": 0.60,
    }

    def __init__(self, decay_rate: float = 0.55):
        self.decay_rate = decay_rate

    def update_risk_scores(
        self,
        graph_model: BuildingGraphModel,
        active_hazards: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculates dynamic risk for all nodes in the building graph based on active hazards."""
        g = graph_model.graph

        # Reset all node risk scores to baseline
        for node in g.nodes():
            g.nodes[node]["risk_score"] = 0.05
            g.nodes[node]["status"] = "SAFE"
            g.nodes[node]["active_hazard"] = None

        if not active_hazards:
            return self._summarize_zones(g)

        # Apply primary hazard risk scores
        hazard_sources = []
        for hazard in active_hazards:
            h_type = str(hazard.get("type", "general")).lower()
            location = str(hazard.get("location", ""))
            base_risk = self.HAZARD_SEVERITY_WEIGHTS.get(h_type, 0.70)

            # Find matching node in graph
            target_node = None
            for node in g.nodes():
                if node.lower() in location.lower() or location.lower() in node.lower():
                    target_node = node
                    break

            if target_node:
                g.nodes[target_node]["risk_score"] = max(g.nodes[target_node]["risk_score"], base_risk)
                g.nodes[target_node]["active_hazard"] = h_type
                hazard_sources.append((target_node, base_risk))

        # Propagate risk through topological graph BFS hops
        for source_node, initial_risk in hazard_sources:
            visited = {source_node}
            queue = collections.deque([(source_node, initial_risk, 0)])

            while queue:
                current_node, current_risk, hops = queue.popleft()
                if hops >= 3:  # Propagate up to 3 graph hops
                    continue

                for neighbor in g.neighbors(current_node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        propagated_risk = round(current_risk * self.decay_rate, 3)
                        existing_risk = g.nodes[neighbor].get("risk_score", 0.05)
                        g.nodes[neighbor]["risk_score"] = max(existing_risk, propagated_risk)
                        queue.append((neighbor, propagated_risk, hops + 1))

        # Update node status categories and edge blockage penalties
        for node, data in g.nodes(data=True):
            r = data.get("risk_score", 0.05)
            if r >= 0.80:
                data["status"] = "CRITICAL"
            elif r >= 0.50:
                data["status"] = "DANGEROUS"
            elif r >= 0.25:
                data["status"] = "CAUTION"
            else:
                data["status"] = "SAFE"

        # Mark high-risk or blocked edges
        for u, v, edge_data in g.edges(data=True):
            max_risk = max(g.nodes[u].get("risk_score", 0.0), g.nodes[v].get("risk_score", 0.0))
            if max_risk >= 0.80:
                edge_data["hazard_blocked"] = True
                edge_data["blockage_penalty"] = 999.0
            elif max_risk >= 0.50:
                edge_data["hazard_blocked"] = False
                edge_data["blockage_penalty"] = 40.0
            else:
                edge_data["hazard_blocked"] = False
                edge_data["blockage_penalty"] = 0.0

        return self._summarize_zones(g)

    def _summarize_zones(self, g: nx.Graph) -> Dict[str, Any]:
        danger_zones = []
        safe_zones = []
        for node, data in g.nodes(data=True):
            entry = {
                "name": node,
                "type": data.get("node_type", "room"),
                "floor_number": data.get("floor_number", 1),
                "risk_score": round(data.get("risk_score", 0.05), 3),
                "status": data.get("status", "SAFE"),
                "hazard": data.get("active_hazard"),
                "occupancy": data.get("occupancy", 0),
            }
            if entry["status"] in {"CRITICAL", "DANGEROUS"}:
                danger_zones.append(entry)
            else:
                safe_zones.append(entry)

        return {
            "danger_zones": sorted(danger_zones, key=lambda x: x["risk_score"], reverse=True),
            "safe_zones": safe_zones,
            "critical_count": sum(1 for z in danger_zones if z["status"] == "CRITICAL"),
            "dangerous_count": sum(1 for z in danger_zones if z["status"] == "DANGEROUS"),
            "safe_count": len(safe_zones),
        }
