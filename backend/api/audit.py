"""Audit log API for administrators."""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.building import AuditEvent
from backend.security.dependencies import get_identity, require_admin

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("")
def list_audit_events(
    request: Request,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
    limit: int = Query(50, ge=1, le=500),
    entity_type: Optional[str] = None,
) -> Any:
    identity = get_identity(request)
    tenant_id = identity.get("tenant_id", "demo")
    query = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    events = query.order_by(AuditEvent.id.desc()).limit(limit).all()
    return {
        "tenant_id": tenant_id,
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "actor": e.actor,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "payload": json.loads(e.payload_json or "{}"),
                "created_at": e.created_at,
            }
            for e in events
        ],
    }
