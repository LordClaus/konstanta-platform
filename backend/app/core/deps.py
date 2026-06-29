"""FastAPI dependencies: identity extraction and role gating.

Thin wrappers over :mod:`app.core.security` so routers depend on small, testable
callables instead of decoding tokens by hand.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security

_bearer = HTTPBearer(auto_error=False)


def _token_from(creds: HTTPAuthorizationCredentials | None) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return creds.credentials


def get_current_staff(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    payload = security.decode_token(_token_from(creds))
    if payload.get("scope") != "staff":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff token required")
    return payload


def require_role(*roles: str):
    """Dependency factory: passes only if the staff token's role is in ``roles``."""

    def dep(staff: dict = Depends(get_current_staff)) -> dict:
        if staff.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return staff

    return dep


def get_current_candidate(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """Optional candidate identity — returns None for missing/invalid tokens so it
    can drive convenience features without forcing login."""
    if creds is None or not creds.credentials:
        return None
    try:
        payload = security.decode_token(creds.credentials)
    except HTTPException:
        return None
    return payload if payload.get("scope") == "candidate" else None
