"""Review business logic."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import AppCache
from app.core.constants import KNOWN_SITES, utcnow_iso
from app.models import Review
from app.schemas.review import ReviewForm
from app.services import serializers


async def warm_cache(session: AsyncSession) -> None:
    rows = (await session.execute(select(Review).order_by(Review.created_at.desc()))).scalars().all()
    AppCache.set_reviews([serializers.review_to_public(r) for r in rows])


def get_public_reviews(site: str | None = None) -> list[dict[str, Any]]:
    """Legacy reviews (no site) are attributed to the original 'konstanta' site."""
    if not site:
        return AppCache.reviews
    return [r for r in AppCache.reviews if (r.get("site") or "konstanta") == site]


async def create_review(session: AsyncSession, data: ReviewForm) -> dict[str, Any]:
    review_id = str(uuid.uuid4())
    created_at = data.createdAt or utcnow_iso()
    review_site = data.site if data.site in KNOWN_SITES else None
    session.add(Review(id=review_id, user_name=data.userName, text=data.text,
                       rating=None, site=review_site))
    await session.flush()
    entry = {
        "id": review_id,
        "userName": data.userName,
        "text": data.text,
        "rating": None,
        "createdAt": created_at,
        "site": review_site,
    }
    AppCache.insert_review(entry)
    return entry
