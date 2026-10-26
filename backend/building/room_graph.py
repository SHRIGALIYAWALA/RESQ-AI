from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx


class BuildingGraphModel:
    """Represents a topological graph of a building's interior and exterior connectivity.
    Nodes: Rooms, Corridors, Staircases, Elevators, Exits, Assembly Points.
    Edges: Doors, Hallway segments, Stair flights with properties (distance_m, capacity, accessibility, status).
    """

    def __init__(self, building_id: int):
        self.building_id = building_id
        self.graph = nx.Graph()

    def add_room_node(self, name: str, floor_number: int = 1, zone: str = "", capacity: int = 25, occupancy: int = 0) -> None:
        self.graph.add_node(
            name,
            node_type="room",
            type="room",
            floor_number=floor_number,
            zone=zone or name,
            capacity=capacity,
            occupancy=occupancy,
            risk_score=0.0,
            status="SAFE",
        )

    def add_corridor_node(self, name: str, floor_number: int = 1, zone: str = "") -> None:
        self.graph.add_node(
            name,
            node_type="corridor",
            type="corridor",
            floor_number=floor_number,
            zone=zone or name,
            risk_score=0.0,
            status="SAFE",
        )

    def add_staircase_node(self, name: str, floor_number: int = 1, connects_floors: Optional[List[int]] = None) -> None:
        self.graph.add_node(
            name,
            node_type="staircase",
            type="staircase",
            floor_number=floor_number,
            connects_floors=connects_floors or [1, 2],
            risk_score=0.0,
            status="SAFE",
        )

    def add_exit_node(self, name: str, floor_number: int = 1, location: str = "") -> None:
        self.graph.add_node(
            name,
            node_type="exit",
            type="exit",
            floor_number=floor_number,
            location=location,
            risk_score=0.0,
            status="SAFE",
        )

    def add_connection(
        self,
        u: str,
        v: str,
        distance_m: float = 10.0,
        door_type: str = "standard",
        status: str = "available",
        accessibility: str = "standard",
    ) -> None:
        if u not in self.graph:
            node_type = "exit" if "exit" in u.lower() else ("corridor" if "corridor" in u.lower() else "room")
            self.graph.add_node(u, node_type=node_type, type=node_type, floor_number=1, risk_score=0.0, status="SAFE")
        if v not in self.graph:
            node_type = "exit" if "exit" in v.lower() else ("corridor" if "corridor" in v.lower() else "room")
            self.graph.add_node(v, node_type=node_type, type=node_type, floor_number=1, risk_score=0.0, status="SAFE")

        self.graph.add_edge(
            u,
            v,
            distance_m=distance_m,
            door_type=door_type,
            status=status,
            accessibility=accessibility,
            hazard_blocked=False,
            blockage_penalty=0.0,
        )

    def get_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({"id": node_id, **data})
        return nodes

    def get_edges(self) -> List[Dict[str, Any]]:
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({"source": u, "target": v, **data})
        return edges

    def get_exits(self) -> List[str]:
        return [node for node, data in self.graph.nodes(data=True) if data.get("node_type") == "exit" or data.get("type") == "exit"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_id": self.building_id,
            "nodes": self.get_nodes(),
            "edges": self.get_edges(),
            "exit_count": len(self.get_exits()),
        }
