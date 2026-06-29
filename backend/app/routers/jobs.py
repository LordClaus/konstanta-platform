from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_session
from app.schemas.job import JobForm
from app.services import job_service, notification_service, storage

router = APIRouter(tags=["jobs"])


@router.get("/jobs")
def get_jobs(site: str | None = None) -> list:
    """Public job list (cache-served). ``?site=`` filters to a candidate site."""
    return job_service.get_public_jobs(site)


@router.post("/jobs", dependencies=[Depends(require_role("admin"))])
async def create_job(data: JobForm, session: AsyncSession = Depends(get_session)) -> dict:
    entry = await job_service.create_job(session, data)
    notification_service.fanout_job_alert(entry)  # fire-and-forget alert to subscribers
    return {"status": "success", "id": entry["id"]}


@router.put("/jobs/{job_id}", dependencies=[Depends(require_role("admin"))])
async def update_job(job_id: str, data: JobForm, session: AsyncSession = Depends(get_session)) -> dict:
    await job_service.update_job(session, job_id, data)
    return {"status": "success", "id": job_id}


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_role("admin"))])
async def delete_job(job_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    await job_service.delete_job(session, job_id)
    return {"status": "success", "id": job_id}


@router.post("/jobs/{job_id}/image", dependencies=[Depends(require_role("admin"))])
async def upload_job_image(job_id: str, file: UploadFile = File(...),
                           session: AsyncSession = Depends(get_session)) -> dict:
    raw = await file.read(storage.MAX_IMAGE_BYTES + 1)
    image_url = storage.upload_job_image(job_id, file.content_type, raw)
    await job_service.set_job_image(session, job_id, image_url)
    return {"status": "success", "id": job_id, "image_url": image_url}
