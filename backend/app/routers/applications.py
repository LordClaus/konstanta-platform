from __future__ import annotations

from fastapi import APIRouter, Depends, Query
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
async def sync_db(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=500, description="page size (max 500)"),
    offset: int = Query(0, ge=0, description="rows to skip"),
) -> list:
    """Applications page for the CRM panel (staff-only), newest-first.
    Paginate with ``?limit=&offset=`` — defaults to the first 100."""
    return await application_service.list_all(session, limit, offset)
