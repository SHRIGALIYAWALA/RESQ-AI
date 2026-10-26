import pytest
from backend.building.room_graph import BuildingGraphModel
from backend.building.zone_manager import DangerZoneEngine


def test_danger_zone_propagation():
    graph_model = BuildingGraphModel(building_id=1)
    graph_model.add_room_node("Room 203", floor_number=2)
    graph_model.add_corridor_node("Corridor C", floor_number=2)
    graph_model.add_room_node("Room 201", floor_number=2)
    graph_model.add_exit_node("Exit A", floor_number=2)

    # Topology: Room 203 <-> Corridor C <-> Room 201 <-> Exit A
    graph_model.add_connection("Room 203", "Corridor C")
    graph_model.add_connection("Corridor C", "Room 201")
    graph_model.add_connection("Room 201", "Exit A")

    engine = DangerZoneEngine(decay_rate=0.5)
    summary = engine.update_risk_scores(graph_model, active_hazards=[{"type": "fire", "location": "Room 203"}])

    g = graph_model.graph
    # Origin of fire should be CRITICAL
    assert g.nodes["Room 203"]["risk_score"] >= 0.8
    assert g.nodes["Room 203"]["status"] == "CRITICAL"

    # Adjacent corridor should receive propagated high risk
    assert g.nodes["Corridor C"]["risk_score"] > 0.4
    assert g.nodes["Corridor C"]["status"] in {"DANGEROUS", "CAUTION"}

    # Distant exit should remain SAFE
    assert g.nodes["Exit A"]["risk_score"] < 0.3
    assert g.nodes["Exit A"]["status"] == "SAFE"
