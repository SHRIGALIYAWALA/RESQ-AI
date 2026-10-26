from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.building import Resource, Building
from backend.api.websocket import ws_manager
from backend.security.dependencies import require_dispatcher

router = APIRouter(tags=["Resources"])


@router.get("/api/resources")
def list_all_resources(db: Session = Depends(get_db)) -> Any:
    resources = db.query(Resource).all()
    return [
        {
            "id": r.id,
            "building_id": r.building_id,
            "name": r.name,
            "resource_type": r.resource_type,
            "status": r.status,
            "location": r.location,
        }
        for r in resources
    ]


@router.post("/api/buildings/{building_id}/resources/{resource_id}/reserve")
async def reserve_resource_api(
    building_id: int,
    resource_id: int,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_dispatcher),
) -> Any:
    resource = db.query(Resource).filter(Resource.id == resource_id, Resource.building_id == building_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.status == "reserved":
        raise HTTPException(status_code=409, detail="Resource already reserved")

    resource.status = "reserved"
    db.commit()
    db.refresh(resource)

    await ws_manager.broadcast({
        "event": "resource_reserved",
        "resource_id": resource.id,
        "building_id": building_id,
        "status": resource.status,
    })

    return {
        "id": resource.id,
        "name": resource.name,
        "status": resource.status,
        "resource_type": resource.resource_type,
    }


@router.post("/api/buildings/{building_id}/resources/{resource_id}/release")
async def release_resource_api(building_id: int, resource_id: int, db: Session = Depends(get_db)) -> Any:
    resource = db.query(Resource).filter(Resource.id == resource_id, Resource.building_id == building_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    resource.status = "available"
    db.commit()
    db.refresh(resource)

    await ws_manager.broadcast({
        "event": "resource_released",
        "resource_id": resource.id,
        "building_id": building_id,
        "status": resource.status,
    })

    return {
        "id": resource.id,
        "name": resource.name,
        "status": resource.status,
        "resource_type": resource.resource_type,
    }
