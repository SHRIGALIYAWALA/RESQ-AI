import hashlib
import hmac
import json
import base64
import time
from typing import Any, Dict, List, Optional
import jwt

from backend.config import get_settings

settings = get_settings()

ROLE_HIERARCHY = {
    "admin": ["admin", "operator", "dispatcher", "responder", "citizen", "viewer"],
    "operator": ["operator", "dispatcher", "responder", "citizen", "viewer"],
    "dispatcher": ["dispatcher", "responder", "citizen", "viewer"],
    "responder": ["responder", "citizen", "viewer"],
    "citizen": ["citizen", "viewer"],
    "viewer": ["viewer"],
}


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Secure password hashing using PBKDF2 with SHA-256."""
    salt_val = salt or "resq-ai-salt-" + hashlib.sha256(password[:4].encode("utf-8")).hexdigest()[:16]
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_val.encode("utf-8"), 100_000)
    return f"pbkdf2:sha256:100000${salt_val}${hashed.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored hash with backward compatibility for legacy hashes."""
    if not password_hash:
        return False
    if password_hash.startswith("pbkdf2:sha256:"):
        parts = password_hash.split("$")
        if len(parts) == 3:
            salt = parts[1]
            return hash_password(password, salt=salt) == password_hash
    # Fallback to legacy sha256
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == password_hash or password == password_hash


def create_access_token(username: str, tenant_id: str, secret: str, expires_minutes: int = 60, role: str = "viewer") -> str:
    """Generate signed JWT access token."""
    now = int(time.time())
    payload = {
        "sub": username,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + (expires_minutes * 60),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    return jwt.decode(token, secret, algorithms=["HS256"])


def has_role(user_role: str, required_role: str) -> bool:
    """Check if user_role has access permissions for required_role."""
    allowed = ROLE_HIERARCHY.get(user_role.lower(), [user_role.lower()])
    return required_role.lower() in allowed
