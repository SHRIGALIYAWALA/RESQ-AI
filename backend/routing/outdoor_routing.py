import math
import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx

from backend.config import get_settings

logger = logging.getLogger("resq_ai.routing.outdoor")


class OutdoorRouteEngine:
    """Calculates outdoor navigation for emergency responders from station to building or assembly points."""

    def __init__(self):
        self.settings = get_settings()

    async def calculate_responder_route(
        self,
        origin_lat_lon: Tuple[float, float],
        destination_lat_lon: Tuple[float, float],
    ) -> Dict[str, Any]:
        """Calculates driving/transit route using OSRM or geodesic distance fallback."""
        orig_lat, orig_lon = origin_lat_lon
        dest_lat, dest_lon = destination_lat_lon

        # Try OSRM public or local server
        if self.settings.routing_provider.lower() == "osrm" and self.settings.osrm_url:
            url = f"{self.settings.osrm_url.rstrip('/')}/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=simplified&geometries=geojson"
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        routes = data.get("routes", [])
                        if routes:
                            route = routes[0]
                            return {
                                "status": "success",
                                "provider": "osrm",
                                "distance_meters": round(route.get("distance", 0.0), 1),
                                "duration_seconds": int(route.get("duration", 0)),
                                "geometry": route.get("geometry", {}),
                                "waypoints": data.get("waypoints", []),
                            }
            except Exception as exc:
                logger.debug(f"OSRM router unavailable: {exc}")

        # Haversine distance fallback
        dist_m = self._haversine(orig_lat, orig_lon, dest_lat, dest_lon)
        est_seconds = int(dist_m / 11.1)  # approx 40 km/h emergency speed
        return {
            "status": "estimated_fallback",
            "provider": "geodesic_heuristic",
            "distance_meters": round(dist_m, 1),
            "duration_seconds": est_seconds,
            "geometry": {
                "type": "LineString",
                "coordinates": [[orig_lon, orig_lat], [dest_lon, dest_lat]],
            },
        }

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c
