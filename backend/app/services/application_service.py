"""Application lifecycle: submit, claim (lock), complete, and read-back.

The claim/complete transitions are expressed as single atomic UPDATEs whose WHERE
clause encodes every invariant, so concurrent managers (browser panel *and* the
Telegram "Take to Work" button) can never double-claim a ticket:

  • claim    → status='new' guard + NOT EXISTS(active ticket for this manager)
  • complete → status='processing' guard + manager_name ownership guard

``perform_lock`` / ``perform_complete`` own their own DB session because they are
also invoked from the bot (outside any request), and they fire the candidate
status notifications + CRM broadcasts as side effects.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import utcnow_iso
from app.db.session import get_sessionmaker
from app.models import Application
from app.schemas.application import ApplicationForm
from app.services import notification_service
from app.services.telegram_gateway import gateway
from app.ws.manager import manager

log = logging.getLogger("api.applications")

# Internal status → candidate-facing status.
_STATUS_MAP = {"new": "received", "processing": "reviewing", "completed": "processed"}


async def create_application(session: AsyncSession, data: ApplicationForm) -> int:
    """Persist a new application and fan out notifications (WS + Telegram + ack)."""
    app = Application(
        name=data.name,
        phone=data.phone,
        email=data.email,
        profession=data.profession,
        comment=data.comment,
        platform=data.platform,
        status="new",
        telegram_chat_id=data.telegram_chat_id,
        lang=data.lang,
    )
    session.add(app)
    await session.flush()
    application_id = app.id

    await manager.broadcast({
        "event": "new_application",
        "application_id": application_id,
        "data": data.model_dump(),
        "timestamp": utcnow_iso(),
    })
    tg_data = data.model_dump()
    tg_data["timestamp"] = utcnow_iso()
    tg_data["platform"] = tg_data.get("platform") or "website"
    await gateway.notify_managers(application_id, tg_data)

    notification_service.notify_candidate(data.email, data.telegram_chat_id, data.lang, "received")
    return application_id


async def get_my_applications(session: AsyncSession, email: str) -> list[dict[str, Any]]:
    rows = (await session.execute(
        select(Application.id, Application.profession, Application.status, Application.created_at)
        .where(Application.email == email)
        .order_by(Application.created_at.desc())
        .limit(50)
    )).all()
    return [
        {
            "id": r[0],
            "profession": r[1],
            "status": _STATUS_MAP.get(r[2], "received"),
            "created_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


async def list_all(session: AsyncSession) -> list[dict[str, Any]]:
    rows = (await session.execute(select(Application).order_by(Application.created_at.desc()))).scalars().all()
    return [
        {
            "id": a.id, "name": a.name, "phone": a.phone, "email": a.email,
            "profession": a.profession, "comment": a.comment, "platform": a.platform,
            "status": a.status, "manager_name": a.manager_name, "consent": a.consent,
            "reason": a.reason, "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]


async def _fetch_contact(session: AsyncSession, application_id) -> tuple:
    row = (await session.execute(
        select(Application.email, Application.telegram_chat_id, Application.lang)
        .where(Application.id == application_id)
    )).first()
    return (row[0], row[1], row[2]) if row else (None, None, None)


async def perform_lock(application_id, manager_name: str) -> tuple[bool, str | None]:
    """Atomically claim a ticket. Shared by the WS endpoint and the bot button."""
    async with get_sessionmaker()() as session:
        try:
            busy = select(Application.id).where(
                Application.manager_name == manager_name,
                Application.status == "processing",
            ).exists()
            result = await session.execute(
                update(Application)
                .where(Application.id == application_id, Application.status == "new", ~busy)
                .values(status="processing", manager_name=manager_name)
            )
            await session.commit()

            if result.rowcount and result.rowcount > 0:
                log.info("Manager %s locked application %s", manager_name, application_id)
                await manager.broadcast({
                    "event": "ticket_locked",
                    "application_id": application_id,
                    "manager_name": manager_name,
                    "timestamp": utcnow_iso(),
                })
                await gateway.handle_ticket_locked(application_id, manager_name)
                email, chat_id, lang = await _fetch_contact(session, application_id)
                notification_service.notify_candidate(email, chat_id, lang, "reviewing")
                return True, None

            # Lock rejected — diagnose the real cause for a precise message.
            busy_row = (await session.execute(
                select(Application.id).where(
                    Application.manager_name == manager_name, Application.status == "processing"
                )
            )).first()
            if busy_row:
                return False, "У вас вже є активна заявка в роботі! Завершіть її спочатку."
            target = (await session.execute(
                select(Application.status).where(Application.id == application_id)
            )).first()
            if not target:
                return False, "Заявку не знайдено."
            if target[0] == "processing":
                return False, "Цю заявку вже взяв інший менеджер."
            if target[0] == "completed":
                return False, "Цю заявку вже завершено."
            return False, "Цю заявку наразі не можна взяти в роботу."
        except Exception as exc:  # noqa: BLE001
            log.error("Database error during lock_ticket: %s", exc)
            return False, "Failed to lock ticket. Please try again."


async def perform_complete(application_id, manager_name) -> tuple[bool, str | None]:
    """Complete an in-progress ticket — only by the manager who claimed it."""
    if not manager_name:
        return False, "Authentication required."
    async with get_sessionmaker()() as session:
        try:
            result = await session.execute(
                update(Application)
                .where(
                    Application.id == application_id,
                    Application.status == "processing",
                    Application.manager_name == manager_name,
                )
                .values(status="completed")
            )
            await session.commit()
            if result.rowcount and result.rowcount > 0:
                log.info("Manager %s completed application %s", manager_name, application_id)
                await manager.broadcast({
                    "event": "ticket_completed",
                    "application_id": application_id,
                    "timestamp": utcnow_iso(),
                })
                email, chat_id, lang = await _fetch_contact(session, application_id)
                notification_service.notify_candidate(email, chat_id, lang, "processed")
                return True, None
            row = (await session.execute(
                select(Application.status, Application.manager_name).where(Application.id == application_id)
            )).first()
            if not row:
                return False, "Заявку не знайдено."
            if row[0] != "processing":
                return False, "Заявка не в роботі."
            return False, "Завершити заявку може лише той, хто взяв її в роботу."
        except Exception as exc:  # noqa: BLE001
            log.error("Database error during complete_ticket: %s", exc)
            return False, "Failed to complete ticket. Please try again."
