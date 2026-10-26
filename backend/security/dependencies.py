"""FastAPI dependencies for JWT identity and role-based access control."""

from typing import Callable, List

from fastapi import HTTPException, Request

from backend.config import get_settings
from backend.security.auth import has_role

settings = get_settings()


def get_identity(request: Request) -> dict:
    """Return request identity from JWT middleware or demo defaults."""
    identity = getattr(request.state, "identity", None)
    if identity:
        return identity
    return {"username": "demo", "tenant_id": "demo", "role": "admin"}


def require_roles(*roles: str) -> Callable[[Request], dict]:
    """Dependency factory: require one of the listed roles when auth is enforced."""

    def _checker(request: Request) -> dict:
        identity = get_identity(request)
        if not settings.require_auth:
            return identity
        user_role = str(identity.get("role", "viewer"))
        if any(has_role(user_role, role) for role in roles):
            return identity
        raise HTTPException(status_code=403, detail=f"Requires one of roles: {', '.join(roles)}")

    return _checker


def require_operator(request: Request) -> dict:
    return require_roles("operator", "admin", "dispatcher")(request)


def require_dispatcher(request: Request) -> dict:
    return require_roles("dispatcher", "admin", "operator")(request)


def require_citizen(request: Request) -> dict:
    return require_roles("citizen", "responder", "dispatcher", "operator", "admin")(request)


def require_responder(request: Request) -> dict:
    return require_roles("responder", "dispatcher", "operator", "admin")(request)


def require_admin(request: Request) -> dict:
    return require_roles("admin")(request)


def log_audit(db, tenant_id: str, action: str, entity_type: str, entity_id: str, actor: str, payload: dict) -> None:
    """Persist an audit event (imported lazily to avoid circular imports)."""
    import json
    import time
    from backend.models.building import AuditEvent

    db.add(AuditEvent(
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload_json=json.dumps(payload),
        created_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    ))
    db.commit()
