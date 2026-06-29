from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_candidate
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.schemas.auth import CandidateLogin, CandidateRegister, GoogleLogin
from app.services import application_service, auth_service

router = APIRouter(tags=["auth:candidate"])


@router.post("/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, data: CandidateRegister,
                   session: AsyncSession = Depends(get_session)) -> dict:
    return await auth_service.candidate_register(session, data)


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, data: CandidateLogin,
                session: AsyncSession = Depends(get_session)) -> dict:
    return await auth_service.candidate_login(session, data)


@router.post("/auth/google")
async def google(data: GoogleLogin, session: AsyncSession = Depends(get_session)) -> dict:
    return await auth_service.candidate_google(session, data)


@router.get("/auth/me")
async def me(candidate: dict | None = Depends(get_current_candidate),
             session: AsyncSession = Depends(get_session)) -> dict:
    if not candidate:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return await auth_service.candidate_profile(session, candidate["sub"])


@router.get("/my-applications")
async def my_applications(candidate: dict | None = Depends(get_current_candidate),
                          session: AsyncSession = Depends(get_session)) -> dict:
    if not candidate:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    email = (candidate.get("email") or "").strip()
    if not email:
        return {"applications": []}
    return {"applications": await application_service.get_my_applications(session, email)}
