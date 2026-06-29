from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.schemas.auth import StaffCreate, StaffLogin
from app.services import auth_service

router = APIRouter(tags=["auth:staff"])


@router.post("/auth/staff/login")
@limiter.limit("5/minute")
async def staff_login(request: Request, data: StaffLogin,
                      session: AsyncSession = Depends(get_session)) -> dict:
    return await auth_service.staff_login(session, data)


@router.post("/admin/staff")
async def create_staff(data: StaffCreate, x_bot_secret: str | None = Header(default=None),
                       session: AsyncSession = Depends(get_session)) -> dict:
    """Provision a staff account. Server-to-server only (X-Bot-Secret header) —
    the bootstrap path for the first admin, used by the owner-only bot command."""
    s = get_settings()
    if not s.bot_provision_secret or x_bot_secret != s.bot_provision_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    return await auth_service.create_staff(session, data)
