import heapq
import logging
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx

from backend.building.room_graph import BuildingGraphModel

logger = logging.getLogger("resq_ai.routing.indoor")


class IndoorRouteEngine:
    """Calculates deterministic safe evacuation paths using weighted Dijkstra and A* algorithms.
    
    Cost Function:
    PathCost = Distance(u, v) + W_danger * Risk(v) + W_congestion * Congestion(v) + BlockagePenalty(u, v) + ExitRisk(target)
    
    The safest route is not necessarily the shortest route.
    """

    def __init__(
        self,
        danger_weight: float = 60.0,
        congestion_weight: float = 20.0,
        blockage_penalty_max: float = 1000.0,
    ):
        self.danger_weight = danger_weight
        self.congestion_weight = congestion_weight
        self.blockage_penalty_max = blockage_penalty_max

    def calculate_safest_route(
        self,
        graph_model: BuildingGraphModel,
        origin_room: str,
        target_exits: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Finds the safest route from origin_room to any of target_exits.
        Evaluates all reachable exits and selects the one with the lowest total safety penalty score.
        """
        g = graph_model.graph
        if origin_room not in g.nodes():
            return None

        available_exits = target_exits or graph_model.get_exits()
        if not available_exits:
            return None

        best_route: Optional[Dict[str, Any]] = None
        min_total_cost = float("inf")

        for exit_node in available_exits:
            if exit_node not in g.nodes():
                continue

            route_info = self._dijkstra_safe_path(g, origin_room, exit_node)
            if route_info and route_info["cost"] < min_total_cost:
                min_total_cost = route_info["cost"]
                best_route = route_info

        return best_route

    def _dijkstra_safe_path(self, g: nx.Graph, origin: str, target: str) -> Optional[Dict[str, Any]]:
        # Priority queue stores (cost, current_node, path_list, cumulative_distance)
        pq: List[Tuple[float, str, List[str], float]] = [(0.0, origin, [origin], 0.0)]
        visited_costs: Dict[str, float] = {origin: 0.0}

        while pq:
            cost, current, path, dist = heapq.heappop(pq)

            if current == target:
                # Calculate aggregate safety score (1.0 is pristine, 0.0 is impassable)
                max_node_risk = max(g.nodes[n].get("risk_score", 0.0) for n in path)
                safety_score = max(0.0, min(1.0, 1.0 - max_node_risk))
                risk_category = "SAFE" if max_node_risk < 0.25 else ("CAUTION" if max_node_risk < 0.5 else "DANGEROUS")

                return {
                    "origin": origin,
                    "target_exit": target,
                    "path": path,
                    "total_distance_m": round(dist, 1),
                    "estimated_time_s": int(dist / 1.2),  # Assuming 1.2 m/s evacuation walking speed
                    "safety_score": round(safety_score, 2),
                    "risk_category": risk_category,
                    "cost": cost,
                }

            if cost > visited_costs.get(current, float("inf")):
                continue

            for neighbor in g.neighbors(current):
                edge_data = g.get_edge_data(current, neighbor) or {}
                node_data = g.nodes[neighbor]

                # If physically or hazard blocked
                if edge_data.get("hazard_blocked", False) or edge_data.get("status") == "blocked":
                    continue

                base_dist = float(edge_data.get("distance_m", 10.0))
                risk_val = float(node_data.get("risk_score", 0.0))
                occ = float(node_data.get("occupancy", 0))
                cap = float(max(1, node_data.get("capacity", 20)))
                congestion_ratio = occ / cap
                penalty = float(edge_data.get("blockage_penalty", 0.0))

                # Weighted step cost
                step_cost = (
                    base_dist
                    + (risk_val * self.danger_weight)
                    + (congestion_ratio * self.congestion_weight)
                    + penalty
                )

                new_cost = cost + step_cost
                new_dist = dist + base_dist

                if new_cost < visited_costs.get(neighbor, float("inf")):
                    visited_costs[neighbor] = new_cost
                    heapq.heappush(pq, (new_cost, neighbor, path + [neighbor], new_dist))

        return None
