from typing import Any, Dict, List, Tuple
from fastapi import APIRouter, Depends, HTTPException
from backend.routing.outdoor_routing import OutdoorRouteEngine

router = APIRouter(prefix="/api/routes", tags=["Routes"])
outdoor_engine = OutdoorRouteEngine()


@router.post("/responder-dispatch")
async def calculate_responder_dispatch_route(payload: Dict[str, Any]) -> Any:
    """Calculates outdoor routing from responder station coordinates to incident building."""
    orig = payload.get("origin_lat_lon", [28.6139, 77.2090])  # [lat, lon]
    dest = payload.get("destination_lat_lon", [28.6289, 77.2065])

    route_res = await outdoor_engine.calculate_responder_route(
        origin_lat_lon=(float(orig[0]), float(orig[1])),
        destination_lat_lon=(float(dest[0]), float(dest[1])),
    )
    return route_res
