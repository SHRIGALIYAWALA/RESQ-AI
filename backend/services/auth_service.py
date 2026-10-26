import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, tenant_id: str, secret: str, expires_minutes: int = 60) -> str:
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError("PyJWT is required when local JWT authentication is enabled") from exc
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {"sub": subject, "tenant_id": tenant_id, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> Dict[str, Any]:
    try:
        import jwt
        return jwt.decode(token, secret, algorithms=["HS256"])
    except ImportError as exc:
        raise RuntimeError("PyJWT is required when local JWT authentication is enabled") from exc
