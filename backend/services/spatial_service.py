"""Spatial queries for building locations using PostGIS or haversine fallback."""

import math
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.building import Building

logger = logging.getLogger("resq_ai.spatial")
settings = get_settings()


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class SpatialService:
    """Building geolocation and proximity queries."""

    def find_nearby_buildings(
        self,
        db: Session,
        latitude: float,
        longitude: float,
        radius_m: float = 5000.0,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        dialect = db.get_bind().dialect.name

        if dialect == "postgresql":
            try:
                return self._postgis_nearby(db, latitude, longitude, radius_m, tenant_id)
            except Exception as exc:
                logger.debug("PostGIS query failed, using haversine: %s", exc)

        return self._haversine_nearby(db, latitude, longitude, radius_m, tenant_id)

    def _postgis_nearby(
        self, db: Session, lat: float, lon: float, radius_m: float, tenant_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        tenant_filter = "AND tenant_id = :tenant_id" if tenant_id else ""
        query = text(f"""
            SELECT id, name, address, latitude, longitude,
                   ST_Distance(
                       geography(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)),
                       geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                   ) AS distance_m
            FROM buildings
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
              {tenant_filter}
              AND ST_DWithin(
                  geography(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)),
                  geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)),
                  :radius
              )
            ORDER BY distance_m
        """)
        params: Dict[str, Any] = {"lat": lat, "lon": lon, "radius": radius_m}
        if tenant_id:
            params["tenant_id"] = tenant_id
        rows = db.execute(query, params).fetchall()
        return [
            {
                "id": row.id,
                "name": row.name,
                "address": row.address,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "distance_m": round(float(row.distance_m), 1),
            }
            for row in rows
        ]

    def _haversine_nearby(
        self, db: Session, lat: float, lon: float, radius_m: float, tenant_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        query = db.query(Building).filter(
            Building.latitude.isnot(None),
            Building.longitude.isnot(None),
        )
        if tenant_id:
            query = query.filter(Building.tenant_id == tenant_id)

        results = []
        for building in query.all():
            dist = haversine_meters(lat, lon, building.latitude, building.longitude)
            if dist <= radius_m:
                results.append({
                    "id": building.id,
                    "name": building.name,
                    "address": building.address,
                    "latitude": building.latitude,
                    "longitude": building.longitude,
                    "distance_m": round(dist, 1),
                })
        results.sort(key=lambda item: item["distance_m"])
        return results

    def set_building_location(
        self, db: Session, building_id: int, latitude: float, longitude: float
    ) -> Optional[Building]:
        building = db.query(Building).filter(Building.id == building_id).first()
        if not building:
            return None
        building.latitude = latitude
        building.longitude = longitude
        db.commit()
        db.refresh(building)
        return building


spatial_service = SpatialService()
