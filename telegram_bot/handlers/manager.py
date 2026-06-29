"""
handlers/manager.py
-------------------
Manager-side logic:
  • format_new_application_message()  — builds the Telegram message + "Take to Work" button
  • handle_take_to_work callback       — locks the ticket via WebSocket and edits the message
  • handle_ticket_locked()            — called from ws_client when another manager locks a ticket
"""

import html
import logging
from typing import Any

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from ..config import settings

log = logging.getLogger(__name__)
router = Router(name="manager")

def _plain_locker(manager_name: str) -> str:
    """Fallback label for a lock NOT initiated through this bot (e.g. the desktop
    CRM): the raw string can't be verified as a Telegram username, so it is shown
    as escaped plain text — never as a fabricated '@mention'. A single-word desktop
    name like 'Dmitriy' therefore renders as 'Dmitriy', not '@Dmitriy'."""
    name = (manager_name or "").strip()
    return html.escape(name) if name else "—"


# ── In-memory registry: application_id → message_id in the managers' group ───
# Used so we can edit the right message when a ticket_locked event arrives.
# Bounded: entries are removed on lock, but tickets that are NEVER claimed would
# otherwise accumulate forever, so we cap the size and evict the oldest (FIFO).
_ticket_message_map: dict[int, int] = {}
_MAX_TRACKED_TICKETS = 500


# ── Keyboard helpers ──────────────────────────────────────────────────────────

def locked_keyboard() -> InlineKeyboardMarkup:
    """Empty keyboard — replaces "Take to Work" after ticket is locked."""
    return InlineKeyboardMarkup(inline_keyboard=[])


# ── Message formatter ─────────────────────────────────────────────────────────

def _format_application(app_id: int, data: dict[str, Any]) -> str:
    name       = data.get("name", "—")
    phone      = data.get("phone", "—")
    email      = data.get("email") or "—"
    profession = data.get("profession") or "—"
    comment    = data.get("comment") or "—"
    platform   = data.get("platform", "website")
    timestamp  = data.get("timestamp", "")

    return (
        f"🔔 <b>New Application #{app_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> {name}\n"
        f"📞 <b>Phone:</b> <code>{phone}</code>\n"
        f"📧 <b>Email:</b> {email}\n"
        f"💼 <b>Profession:</b> {profession}\n"
        f"💬 <b>Comment:</b> {comment}\n"
        f"📲 <b>Platform:</b> {platform}\n"
        f"🕐 <b>Time:</b> {timestamp}"
    )


# ── Called by the API (backend) when a new application arrives ────────────────

async def notify_managers(bot: Bot, application_id: int, data: dict[str, Any]) -> None:
    """
    Send a formatted notification to MANAGER_GROUP_ID with a "Take to Work" button.
    Saves the sent message_id so we can edit it later.
    """
    text = _format_application(application_id, data)

    try:
        # Notification only — NO "Take to Work" button. Claiming a ticket happens
        # exclusively in the admin panel (real staff accounts); a bot-group claim had
        # no account behind it and no way to be completed.
        sent: Message = await bot.send_message(
            chat_id=settings.manager_group_id,
            text=text,
            parse_mode="HTML",
        )
        _ticket_message_map[application_id] = sent.message_id
        # Evict oldest entries so unclaimed tickets can't grow the map without bound.
        while len(_ticket_message_map) > _MAX_TRACKED_TICKETS:
            _ticket_message_map.pop(next(iter(_ticket_message_map)), None)
        log.info("Notified managers about application #%s (msg_id=%s)", application_id, sent.message_id)
    except Exception as exc:
        log.error("Failed to notify managers about application #%s: %s", application_id, exc)


# ── Lightweight broadcast notifications (no action buttons) ───────────────────

async def notify_new_review(bot: Bot, user_name: str, text: str) -> None:
    """Notify the managers' group about a newly submitted website review."""
    body = (
        f"📝 <b>New review</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {html.escape(user_name or '—')}\n"
        f"💬 {html.escape((text or '')[:500])}"
    )
    try:
        await bot.send_message(chat_id=settings.manager_group_id, text=body, parse_mode="HTML")
    except Exception as exc:
        log.error("Failed to notify group about new review: %s", exc)


async def notify_new_registration(bot: Bot, full_name: str, email: str) -> None:
    """Notify the managers' group about a new candidate registration."""
    body = (
        f"🆕 <b>New candidate registration</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {html.escape(full_name or '—')}\n"
        f"📧 {html.escape(email or '—')}"
    )
    try:
        await bot.send_message(chat_id=settings.manager_group_id, text=body, parse_mode="HTML")
    except Exception as exc:
        log.error("Failed to notify group about new registration: %s", exc)


# ── Called by the API (perform_lock) right after a successful lock ────────────

async def handle_ticket_locked(
    bot: Bot, application_id: int, manager_name: str
) -> None:
    """
    Edits the managers' group message to show who took the ticket and removes the
    "Take to Work" button so others can't click it. Pops the map entry afterwards
    (W8: prevents unbounded growth of _ticket_message_map).
    """
    # Locks now come only from the admin panel, so manager_name is a real staff name.
    locker = _plain_locker(manager_name)

    message_id = _ticket_message_map.pop(application_id, None)
    if not message_id:
        log.warning("ticket_locked for #%s but no message_id in map.", application_id)
        return

    try:
        await bot.edit_message_text(
            chat_id=settings.manager_group_id,
            message_id=message_id,
            text=(
                f"✅ <b>Application #{application_id} has been taken to work</b>\n"
                f"by {locker}"
            ),
            parse_mode="HTML",
            reply_markup=locked_keyboard(),
        )
        log.info("Edited message for locked ticket #%s by %s", application_id, manager_name)
    except TelegramBadRequest as exc:
        # Message might already be edited — that's fine
        log.warning("Could not edit locked ticket message #%s: %s", application_id, exc)
    except Exception as exc:
        log.error("Error handling ticket_locked for #%s: %s", application_id, exc)


# ── Taking a ticket "to work" is panel-only ───────────────────────────────────
# The Telegram group is notification-only: there is no "Take to Work" button and no
# take_work callback handler. Claiming (perform_lock) and completing (perform_complete)
# are driven by the admin panel over the WebSocket, where every action is tied to a
# real staff account. perform_lock still calls handle_ticket_locked() above to edit the
# group message so managers can see a ticket was claimed.
