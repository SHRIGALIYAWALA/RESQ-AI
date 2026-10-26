from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.database import get_db
from backend.models.building import User
from backend.security.auth import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])
settings = get_settings()


@router.post("/register")
def register_user(payload: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    tenant_id = str(payload.get("tenant_id", "demo")).strip() or "demo"

    if len(username) < 3 or len(password) < 8:
        raise HTTPException(status_code=400, detail="Username must have 3 characters and password 8 characters")

    if db.query(User).filter(User.username == username).first() is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    requested_role = str(payload.get("role", "viewer")).lower()
    valid_roles = {"viewer", "operator", "admin", "dispatcher", "responder", "citizen"}
    role = requested_role if requested_role in valid_roles and settings.app_env.lower() == "demo" else "viewer"

    user = User(
        username=username,
        password_hash=hash_password(password),
        tenant_id=tenant_id,
        role=role,
    )
    db.add(user)
    db.commit()
    return {"username": username, "tenant_id": tenant_id, "role": user.role}


@router.post("/token")
def login_user(payload: Dict[str, Any], response: Response, db: Session = Depends(get_db)) -> Any:
    username = str(payload.get("username", ""))
    password = str(payload.get("password", ""))

    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        username=user.username,
        tenant_id=user.tenant_id,
        secret=settings.auth_secret,
        expires_minutes=settings.access_token_minutes,
        role=user.role,
    )
    response.set_cookie(
        key="resq_access_token",
        value=token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.app_env.lower() in {"production", "prod"},
        samesite="lax",
        path="/",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": user.tenant_id,
        "role": user.role,
        "username": user.username,
    }


@router.get("/session")
def get_session(request: Request) -> Any:
    token = request.cookies.get("resq_access_token", "")
    if not token:
        return {"authenticated": False}
    try:
        identity = decode_access_token(token, settings.auth_secret)
    except Exception:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "username": identity.get("sub", ""),
        "role": identity.get("role", "viewer"),
    }


@router.post("/logout")
def logout_user(response: Response) -> Any:
    response.delete_cookie(
        key="resq_access_token",
        path="/",
        httponly=True,
        secure=settings.app_env.lower() in {"production", "prod"},
        samesite="lax",
    )
    return {"status": "logged_out"}
