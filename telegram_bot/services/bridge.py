"""
services/bridge.py
------------------
Runtime dependency-injection slot that lets the bot's handlers call back into the
API process WITHOUT importing it (which would create a circular import:
app.services.telegram → telegram_bot.handlers, and handlers → the API).

The API (app/services/telegram.py) assigns `bridge.lock_ticket = perform_lock` on startup.
Handlers call `bridge.lock_ticket(...)` at runtime; it's None until injected.
"""

from typing import Awaitable, Callable, Optional

# async (application_id: int, manager_name: str) -> tuple[bool, str | None]
#   (True, None)          → ticket locked (side effects done by the API: broadcast +
#                           Telegram group message edit)
#   (False, "<reason>")   → rejected / unavailable
lock_ticket: Optional[Callable[[int, str], Awaitable["tuple[bool, str | None]"]]] = None
