"""Category business logic (admin-managed; shared across candidate sites)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import AppCache
from app.core.constants import DEFAULT_CATEGORIES, slug
from app.models import Category, Job
from app.schemas.category import CategoryForm
from app.services import serializers


async def warm_cache(session: AsyncSession) -> None:
    rows = (await session.execute(select(Category).order_by(Category.label_en))).scalars().all()
    AppCache.set_categories([serializers.category_to_public(c) for c in rows])


async def seed_defaults(session: AsyncSession) -> None:
    """Seed the four default categories when the table is empty."""
    count = (await session.execute(select(func.count()).select_from(Category))).scalar_one()
    if count:
        return
    for cid, ua, cz, en in DEFAULT_CATEGORIES:
        session.add(Category(id=cid, label_ua=ua, label_cz=cz, label_en=en))
    await session.flush()


def get_public_categories() -> list[dict[str, Any]]:
    return AppCache.categories


async def create_category(session: AsyncSession, data: CategoryForm) -> str:
    label_en = (data.label_en or "").strip()
    if not data.label_ua.strip() or not data.label_cz.strip() or not label_en:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "All three labels (UA/CZ/EN) are required")
    cat_id = slug(label_en)
    if await session.get(Category, cat_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists")
    session.add(Category(id=cat_id, label_ua=data.label_ua.strip(),
                         label_cz=data.label_cz.strip(), label_en=label_en))
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists") from exc
    await warm_cache(session)
    return cat_id


async def update_category(session: AsyncSession, cat_id: str, data: CategoryForm) -> None:
    if not data.label_ua.strip() or not data.label_cz.strip() or not data.label_en.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "All three labels (UA/CZ/EN) are required")
    cat = await session.get(Category, cat_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    cat.label_ua, cat.label_cz, cat.label_en = (
        data.label_ua.strip(), data.label_cz.strip(), data.label_en.strip(),
    )
    await session.flush()
    await warm_cache(session)


async def delete_category(session: AsyncSession, cat_id: str) -> None:
    # Refuse to delete a category still used by jobs — those jobs would lose their
    # filter category. The admin must reassign/delete them first.
    in_use = (await session.execute(
        select(func.count()).select_from(Job).where(Job.type == cat_id)
    )).scalar_one()
    if in_use:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Category is used by {in_use} job(s); reassign them first")
    cat = await session.get(Category, cat_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    await session.delete(cat)
    await warm_cache(session)
