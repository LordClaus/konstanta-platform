from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_staff
from app.db.session import get_session
from app.schemas.application import ApplicationForm
from app.services import application_service

router = APIRouter(tags=["applications"])


@router.post("/apply")
async def submit_application(data: ApplicationForm,
                             session: AsyncSession = Depends(get_session)) -> dict:
    await application_service.create_application(session, data)
    return {"status": "success", "message": "Application saved to DB successfully"}


@router.get("/sync-db", dependencies=[Depends(get_current_staff)])
async def sync_db(session: AsyncSession = Depends(get_session)) -> list:
    """Full applications dump for the CRM panel (staff-only)."""
    return await application_service.list_all(session)
