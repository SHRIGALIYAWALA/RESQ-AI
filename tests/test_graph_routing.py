import pytest
from backend.building.room_graph import BuildingGraphModel
from backend.routing.indoor_routing import IndoorRouteEngine
from backend.routing.safe_path import SafePathCoordinator


def test_dijkstra_safe_routing_basic():
    graph_model = BuildingGraphModel(building_id=1)
    graph_model.add_room_node("Room 201", floor_number=2)
    graph_model.add_room_node("Room 202", floor_number=2)
    graph_model.add_corridor_node("Corridor North", floor_number=2)
    graph_model.add_corridor_node("Corridor South", floor_number=2)
    graph_model.add_exit_node("Exit A", floor_number=2)
    graph_model.add_exit_node("Exit B", floor_number=2)

    # Connections
    graph_model.add_connection("Room 201", "Corridor North", distance_m=10.0)
    graph_model.add_connection("Corridor North", "Exit A", distance_m=15.0)

    graph_model.add_connection("Room 201", "Corridor South", distance_m=12.0)
    graph_model.add_connection("Corridor South", "Exit B", distance_m=20.0)

    engine = IndoorRouteEngine()
    route = engine.calculate_safest_route(graph_model, origin_room="Room 201")

    assert route is not None
    assert route["target_exit"] == "Exit A"
    assert route["path"] == ["Room 201", "Corridor North", "Exit A"]
    assert route["total_distance_m"] == 25.0
    assert route["safety_score"] == 1.0


def test_dijkstra_rerouting_around_danger():
    graph_model = BuildingGraphModel(building_id=1)
    graph_model.add_room_node("Room 201", floor_number=2)
    graph_model.add_corridor_node("Corridor North", floor_number=2)
    graph_model.add_corridor_node("Corridor South", floor_number=2)
    graph_model.add_exit_node("Exit A", floor_number=2)
    graph_model.add_exit_node("Exit B", floor_number=2)

    graph_model.add_connection("Room 201", "Corridor North", distance_m=10.0)
    graph_model.add_connection("Corridor North", "Exit A", distance_m=15.0)

    graph_model.add_connection("Room 201", "Corridor South", distance_m=12.0)
    graph_model.add_connection("Corridor South", "Exit B", distance_m=20.0)

    # Fire in Corridor North (makes it high risk)
    graph_model.graph.nodes["Corridor North"]["risk_score"] = 0.95

    engine = IndoorRouteEngine()
    route = engine.calculate_safest_route(graph_model, origin_room="Room 201")

    assert route is not None
    # Must detour to Exit B via Corridor South because Corridor North is dangerous!
    assert route["target_exit"] == "Exit B"
    assert route["path"] == ["Room 201", "Corridor South", "Exit B"]


def test_safe_path_coordinator_room_instructions():
    graph_model = BuildingGraphModel(building_id=1)
    graph_model.add_room_node("Room 201", floor_number=2)
    graph_model.add_room_node("Room 202", floor_number=2)
    graph_model.add_corridor_node("Corridor North", floor_number=2)
    graph_model.add_exit_node("Exit A", floor_number=2)

    graph_model.add_connection("Room 201", "Corridor North", distance_m=10.0)
    graph_model.add_connection("Room 202", "Corridor North", distance_m=10.0)
    graph_model.add_connection("Corridor North", "Exit A", distance_m=15.0)

    coordinator = SafePathCoordinator()
    plan = coordinator.generate_evacuation_plan(graph_model, active_hazards=[{"type": "fire", "location": "Room 202"}])

    assert "Exit A" in plan["safe_exits"]
    assert "Room 201" in plan["room_instructions"]
    assert "Room 202" in plan["room_instructions"]
    assert "Exit A" in plan["room_instructions"]["Room 201"]
