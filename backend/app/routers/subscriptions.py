from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_session
from app.schemas.subscription import SubscribeForm, UnsubscribeForm
from app.services import notification_service, subscription_service

router = APIRouter(tags=["subscriptions"])


@router.post("/subscribe")
@limiter.limit("10/minute")
async def subscribe(request: Request, form: SubscribeForm,
                    session: AsyncSession = Depends(get_session)) -> dict:
    await subscription_service.subscribe(session, form)
    return {"status": "success"}


@router.post("/unsubscribe")
@limiter.limit("10/minute")
async def unsubscribe(request: Request, form: UnsubscribeForm,
                      session: AsyncSession = Depends(get_session)) -> dict:
    await subscription_service.unsubscribe(session, form)
    return {"status": "success"}


@router.get("/unsubscribe")
async def unsubscribe_link(e: str, k: str, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    """One-click unsubscribe for alert emails (HMAC-signed, no login)."""
    email = (e or "").strip().lower()
    ok = bool(email) and hmac.compare_digest(k or "", notification_service.unsub_sig(email))
    if ok:
        try:
            await subscription_service.unsubscribe_email(session, email)
        except Exception:  # noqa: BLE001
            ok = False
    msg = "You have been unsubscribed from job alerts." if ok else "Invalid or expired unsubscribe link."
    return HTMLResponse(
        "<!doctype html><meta charset=utf-8>"
        "<div style='font-family:sans-serif;max-width:480px;margin:60px auto;text-align:center;color:#1a2b4b'>"
        f"<h2>{msg}</h2></div>"
    )
