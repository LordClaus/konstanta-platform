"""Authentication primitives: password hashing, JWT issue/verify, Google OAuth,
and the 18+ age gate.

Two realms share one JWT mechanism:
  • staff     (scope="staff", role ∈ {admin, worker}) — internal CRM users.
  • candidate (scope="candidate")                     — public-site users.

Password hashing uses bcrypt directly (passlib 1.7.x is broken against bcrypt 5.x).
Secrets come from validated settings, so importing this module never crashes a
test that hasn't set JWT_SECRET (a safe default is used in non-production).
"""

from __future__ import annotations

import time
from datetime import date

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.config import get_settings


# ── Passwords ─────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """bcrypt hash (cost 12). Store the returned string in ``password_hash``."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_token(sub: str, scope: str, ttl: int, **extra) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {"sub": str(sub), "scope": scope, "iat": now, "exp": now + ttl, **extra}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_alg)


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_alg])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc


def create_staff_token(staff_id, username: str, role: str) -> str:
    return create_token(
        staff_id, "staff", get_settings().staff_ttl_seconds, username=username, role=role
    )


def create_candidate_token(user_id, email: str) -> str:
    return create_token(
        user_id, "candidate", get_settings().candidate_ttl_seconds, email=email
    )


# ── Google OAuth ──────────────────────────────────────────────────────────────
def verify_google(id_token_str: str) -> dict:
    """Verify a Google ID token server-side. Returns {sub, email, name}."""
    client_id = get_settings().google_client_id
    if not client_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Google login is not configured")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        info = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), client_id
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google token") from exc
    return {"sub": info["sub"], "email": info.get("email", ""), "name": info.get("name", "")}


# ── Age gate ──────────────────────────────────────────────────────────────────
def assert_adult(birth: date) -> None:
    """Raise 400 if the person is younger than 18 today."""
    today = date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    if age < 18:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Registration is allowed from age 18.")
