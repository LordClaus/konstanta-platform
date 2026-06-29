"""Job-alert subscription management."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import AppCache
from app.core.constants import KNOWN_SITES, normalize_lang
from app.models import Subscription
from app.schemas.subscription import SubscribeForm, UnsubscribeForm


async def subscribe(session: AsyncSession, form: SubscribeForm) -> None:
    email = ((form.email or "").strip().lower()) or None
    chat_id = form.telegram_chat_id
    if not email and not chat_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide an email or a Telegram chat id")
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid email")

    category = (form.category or "").strip() or None
    if category and not AppCache.has_category(category):
        category = None  # unknown category → subscribe to all
    site = form.site if form.site in KNOWN_SITES else None
    lang = normalize_lang(form.lang)

    # Dedupe the exact (recipient, category, site) tuple before inserting.
    if email:
        await session.execute(
            delete(Subscription).where(
                Subscription.email == email,
                Subscription.category.is_(category) if category is None else Subscription.category == category,
                Subscription.site.is_(site) if site is None else Subscription.site == site,
            )
        )
    if chat_id:
        await session.execute(
            delete(Subscription).where(
                Subscription.telegram_chat_id == chat_id,
                Subscription.category.is_(category) if category is None else Subscription.category == category,
                Subscription.site.is_(site) if site is None else Subscription.site == site,
            )
        )
    session.add(Subscription(email=email, telegram_chat_id=chat_id, category=category, site=site, lang=lang))


async def unsubscribe(session: AsyncSession, form: UnsubscribeForm) -> None:
    if not (form.email or form.telegram_chat_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide an email or a Telegram chat id")
    if form.email:
        await session.execute(delete(Subscription).where(Subscription.email == form.email.strip().lower()))
    if form.telegram_chat_id:
        await session.execute(delete(Subscription).where(Subscription.telegram_chat_id == form.telegram_chat_id))


async def unsubscribe_email(session: AsyncSession, email: str) -> None:
    await session.execute(delete(Subscription).where(Subscription.email == email.strip().lower()))
