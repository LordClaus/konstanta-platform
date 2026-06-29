"""Job business logic: CRUD against the DB plus in-place cache maintenance.

Reads are served from :class:`AppCache`; writes update both the DB (source of
truth) and the cache so a successful write is immediately visible without a
full table re-read.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import AppCache
from app.core.constants import clean_cities, clean_sites, utcnow_iso
from app.models import Job
from app.schemas.job import JobForm
from app.services import serializers


def get_public_jobs(site: str | None = None) -> list[dict[str, Any]]:
    """Cache-served list. ``?site=`` returns jobs assigned to that site plus the
    legacy "everywhere" jobs (empty ``sites``)."""
    if not site:
        return AppCache.jobs
    return [j for j in AppCache.jobs if not j.get("sites") or site in j["sites"]]


async def warm_cache(session: AsyncSession) -> None:
    """Load every job into the cache, newest-first (called at startup)."""
    rows = (await session.execute(select(Job).order_by(Job.created_at.desc()))).scalars().all()
    AppCache.set_jobs([serializers.job_to_public(j) for j in rows])


async def create_job(session: AsyncSession, data: JobForm) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    created_at = utcnow_iso()
    cities = clean_cities(data.cities)
    job = Job(
        id=job_id,
        title_ua=data.title_ua,
        title_cz=data.title_cz,
        title_en=data.title_en,
        type=data.type,
        location=serializers.job_location(data, cities),
        salary=data.salary,
        description=data.description,
        is_new=bool(data.is_new),
        sites=clean_sites(data.sites),
        cities=cities,
    )
    session.add(job)
    await session.flush()
    entry = serializers.job_form_to_public(job_id, data, created_at)
    AppCache.insert_job(entry)
    return entry


async def update_job(session: AsyncSession, job_id: str, data: JobForm) -> dict[str, Any]:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    cities = clean_cities(data.cities)
    job.title_ua, job.title_cz, job.title_en = data.title_ua, data.title_cz, data.title_en
    job.type = data.type
    job.location = serializers.job_location(data, cities)
    job.salary = data.salary
    job.description = data.description
    job.is_new = bool(data.is_new)
    job.sites = clean_sites(data.sites)
    job.cities = cities
    await session.flush()
    entry = serializers.job_form_to_public(job_id, data, None, image_url=job.image_url)
    if not AppCache.replace_job(entry):
        await warm_cache(session)
    return entry


async def delete_job(session: AsyncSession, job_id: str) -> None:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    await session.delete(job)
    AppCache.remove_job(job_id)


async def set_job_image(session: AsyncSession, job_id: str, image_url: str) -> None:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    job.image_url = image_url
    await session.flush()
    AppCache.set_job_image(job_id, image_url)


# Kept for completeness: the cities list is stored as JSON natively, but a couple
# of older call sites still expect a serialized string.
def cities_json(cities: list[dict[str, Any]]) -> str:
    return json.dumps(cities, ensure_ascii=False)
