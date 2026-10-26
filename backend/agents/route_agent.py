from typing import Any, Dict, List, Optional, Tuple

from backend.routing.outdoor_routing import OutdoorRouteEngine


class RouteAgent:
    """Specialized agent responsible for calculating responder transit routes and handling dynamic path blockages."""

    name = "ROUTE_AGENT"

    def __init__(self):
        self.outdoor_engine = OutdoorRouteEngine()

    async def get_responder_dispatch_route(
        self,
        responder_station_coords: Tuple[float, float],
        building_coords: Tuple[float, float],
    ) -> Dict[str, Any]:
        route = await self.outdoor_engine.calculate_responder_route(responder_station_coords, building_coords)
        return {
            "agent": self.name,
            "status": "completed",
            "navigation": route,
            "estimated_eta_minutes": round(route.get("duration_seconds", 300) / 60.0, 1),
            "distance_km": round(route.get("distance_meters", 1000) / 1000.0, 2),
        }
