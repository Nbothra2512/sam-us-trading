# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""JWT authentication — single-user login for SAM dashboard."""
import os
import logging
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from fastapi import Request, HTTPException, WebSocket
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Config from environment
SECRET_KEY = os.getenv("SAM_JWT_SECRET", "sam-default-secret-change-me")
SAM_USERNAME = os.getenv("SAM_USERNAME", "admin")
SAM_PASSWORD_HASH = os.getenv("SAM_PASSWORD_HASH", "")
TOKEN_EXPIRY_HOURS = int(os.getenv("SAM_TOKEN_EXPIRY_HOURS", "24"))


def _hash_password(password: str) -> str:
    """Hash password with SHA-256 + secret salt."""
    return sha256(f"{password}:{SECRET_KEY}".encode()).hexdigest()


def _create_token(username: str) -> str:
    """Create a simple JWT-like token (base64 encoded payload + signature)."""
    import base64
    import json
    import hmac

    payload = {
        "sub": username,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def _verify_token(token: str) -> dict | None:
    """Verify token and return payload, or None if invalid."""
    import base64
    import json
    import hmac

    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Pad base64
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        # Check expiry
        if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
            return None

        return payload
    except Exception:
        return None


def login(username: str, password: str) -> dict:
    """Authenticate user and return token."""
    if not SAM_PASSWORD_HASH:
        # No password set — auth disabled, return token
        logger.warning("SAM_PASSWORD_HASH not set — auth is disabled!")
        return {"token": _create_token(username), "username": username}

    if username != SAM_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if _hash_password(password) != SAM_PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": _create_token(username), "username": username}


def require_auth(request: Request) -> dict:
    """Extract and verify token from Authorization header. Returns payload."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header[7:]
    payload = _verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


def verify_ws_token(token: str) -> bool:
    """Verify token for WebSocket connections (passed as query param)."""
    if not SAM_PASSWORD_HASH:
        return True  # Auth disabled
    return _verify_token(token) is not None


def generate_password_hash(password: str) -> str:
    """Utility: generate hash for a password (for setting SAM_PASSWORD_HASH env var)."""
    return _hash_password(password)
