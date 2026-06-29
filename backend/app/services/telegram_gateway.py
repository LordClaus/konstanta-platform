"""Single outbound seam to the in-process Telegram bot.

Services never import aiogram or the bot package directly; they call this gateway,
which holds the live bot + the ``telegram_bot.handlers.manager`` module (injected
at startup by :mod:`app.services.telegram`). Every method is a safe no-op when the
bot is disabled (no BOT_TOKEN), so the API runs fine without Telegram configured.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("api.telegram")


class TelegramGateway:
    def __init__(self) -> None:
        self.bot: Any = None
        self.mgr: Any = None  # telegram_bot.handlers.manager module

    @property
    def enabled(self) -> bool:
        return self.bot is not None and self.mgr is not None

    def bind(self, bot: Any, mgr: Any) -> None:
        self.bot, self.mgr = bot, mgr

    def reset(self) -> None:
        self.bot = self.mgr = None

    async def send_message(self, chat_id: Any, text: str) -> None:
        if not (self.bot is not None and chat_id):
            return
        try:
            await self.bot.send_message(chat_id, text)
        except Exception as exc:  # noqa: BLE001
            log.warning("Telegram send failed for %s: %s", chat_id, exc)

    async def notify_managers(self, application_id: int, data: dict) -> None:
        if not self.enabled:
            return
        try:
            await self.mgr.notify_managers(self.bot, application_id, data)
        except Exception as exc:  # noqa: BLE001
            log.error("notify_managers failed for #%s: %s", application_id, exc)

    async def notify_new_review(self, user_name: str, text: str) -> None:
        if not self.enabled:
            return
        try:
            await self.mgr.notify_new_review(self.bot, user_name, text)
        except Exception as exc:  # noqa: BLE001
            log.error("notify_new_review failed: %s", exc)

    async def notify_new_registration(self, full_name: str, email: str) -> None:
        if not self.enabled:
            return
        try:
            await self.mgr.notify_new_registration(self.bot, full_name, email)
        except Exception as exc:  # noqa: BLE001
            log.error("notify_new_registration failed: %s", exc)

    async def handle_ticket_locked(self, application_id: int, manager_name: str) -> None:
        if not self.enabled:
            return
        try:
            await self.mgr.handle_ticket_locked(self.bot, application_id, manager_name)
        except Exception as exc:  # noqa: BLE001
            log.error("handle_ticket_locked failed for #%s: %s", application_id, exc)


gateway = TelegramGateway()
