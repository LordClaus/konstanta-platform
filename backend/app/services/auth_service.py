"""Authentication/account business logic for both realms (staff + candidate)."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.constants import utcnow_iso
from app.models import Staff, User
from app.schemas.auth import (
    CandidateLogin,
    CandidateRegister,
    GoogleLogin,
    StaffCreate,
    StaffLogin,
)
from app.services.telegram_gateway import gateway
from app.ws.manager import manager

log = logging.getLogger("api.auth")


# ── Staff ─────────────────────────────────────────────────────────────────────
async def staff_login(session: AsyncSession, data: StaffLogin) -> dict:
    staff = (await session.execute(
        select(Staff).where(Staff.username == data.username)
    )).scalar_one_or_none()
    if not staff or not staff.is_active or not security.verify_password(data.password, staff.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token = security.create_staff_token(staff.id, staff.username, staff.role)
    return {"access_token": token, "token_type": "bearer", "role": staff.role, "username": staff.username}


async def create_staff(session: AsyncSession, data: StaffCreate) -> dict:
    if data.role not in ("admin", "worker"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be 'admin' or 'worker'")
    if len(data.password) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password too short (min 6 chars)")
    session.add(Staff(
        username=data.username,
        password_hash=security.hash_password(data.password),
        role=data.role,
        full_name=data.full_name,
    ))
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists") from exc
    log.info("Staff provisioned: %s (%s)", data.username, data.role)
    return {"status": "success", "username": data.username, "role": data.role}


# ── Candidate ─────────────────────────────────────────────────────────────────
async def candidate_register(session: AsyncSession, data: CandidateRegister) -> dict:
    security.assert_adult(data.birthdate)  # → 400 if < 18
    email = data.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid email")
    if len(data.password) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password too short (min 6 chars)")
    if (await session.execute(select(User.id).where(User.email == email))).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=email, password_hash=security.hash_password(data.password),
                full_name=data.full_name, birthdate=data.birthdate)
    session.add(user)
    await session.flush()

    await manager.broadcast({
        "event": "new_registration", "email": email,
        "full_name": data.full_name, "timestamp": utcnow_iso(),
    })
    await gateway.notify_new_registration(data.full_name, email)

    token = security.create_candidate_token(user.id, email)
    return {"access_token": token, "token_type": "bearer", "full_name": data.full_name, "email": email}


async def candidate_login(session: AsyncSession, data: CandidateLogin) -> dict:
    email = data.email.strip().lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not security.verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = security.create_candidate_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer", "full_name": user.full_name, "email": user.email}


async def candidate_google(session: AsyncSession, data: GoogleLogin) -> dict:
    info = security.verify_google(data.id_token)  # → 401 if invalid
    email = (info["email"] or "").strip().lower()
    sub, name = info["sub"], info["name"]
    user = (await session.execute(
        select(User).where(or_(User.google_sub == sub, User.email == email))
    )).scalar_one_or_none()
    if user:
        user.google_sub = sub
        full_name = user.full_name or name
        user_id = user.id
    else:
        user = User(email=email, google_sub=sub, full_name=name)
        session.add(user)
        await session.flush()
        user_id, full_name = user.id, name
    token = security.create_candidate_token(user_id, email)
    return {"access_token": token, "token_type": "bearer", "full_name": full_name, "email": email}


async def candidate_profile(session: AsyncSession, user_id) -> dict:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {"email": user.email, "full_name": user.full_name}
