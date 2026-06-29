"""In-process Telegram bot lifecycle (webhook in prod, long-polling locally).

Entirely optional: when ``BOT_TOKEN`` is unset the API runs without a bot. On
startup we wire the bot's "Take to Work" button back to the application service
(``bridge.lock_ticket``) and bind the outbound :data:`gateway` so services can
push messages to Telegram.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from app.config import get_settings
from app.services.application_service import perform_lock
from app.services.telegram_gateway import gateway

log = logging.getLogger("api.telegram")

# Ensure the sibling telegram_bot/ package (repo root) is importable.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_bot = None
_dp = None
_poll_task: asyncio.Task | None = None


def get_bot():
    return _bot


def get_dispatcher():
    return _dp


async def start() -> None:
    global _bot, _dp, _poll_task
    s = get_settings()
    if not s.bot_token:
        log.info("Telegram bot disabled (BOT_TOKEN not set).")
        return
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.enums import ParseMode
        from aiogram.fsm.storage.memory import MemoryStorage
        from telegram_bot.handlers import manager as manager_module
        from telegram_bot.handlers.admin import router as admin_router
        from telegram_bot.handlers.candidate import router as candidate_router
        from telegram_bot.handlers.manager import router as manager_router
        from telegram_bot.services import bridge
    except Exception as exc:  # noqa: BLE001
        log.error("Telegram bot import failed; running API without bot: %s", exc)
        return

    try:
        session = AiohttpSession()
        session.timeout = 20.0
        bot = Bot(token=s.bot_token, session=session,
                  default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(admin_router)
        dp.include_router(candidate_router)
        dp.include_router(manager_router)

        bridge.lock_ticket = perform_lock  # bot button → application service, in-process
        gateway.bind(bot, manager_module)
        _bot, _dp = bot, dp
    except Exception as exc:  # noqa: BLE001
        log.error("Telegram bot setup failed; API continues without bot: %s", exc)
        gateway.reset()
        _bot = _dp = None
        return

    public_url = s.public_base_url
    try:
        if public_url:
            url = f"{public_url}/telegram/webhook"
            await bot.set_webhook(
                url=url,
                secret_token=s.bot_provision_secret or None,
                drop_pending_updates=False,
                allowed_updates=dp.resolve_used_update_types(),
            )
            log.info("Telegram bot ready (webhook → %s).", url)
        else:
            await bot.delete_webhook(drop_pending_updates=True)
            _poll_task = asyncio.create_task(dp.start_polling(bot), name="tg_polling")
            log.info("Telegram bot ready (long-polling; no PUBLIC_URL set).")
    except Exception as exc:  # noqa: BLE001
        log.warning("Webhook/polling setup failed; bot stays enabled: %s", exc)


async def stop() -> None:
    global _poll_task
    if _poll_task is not None:
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
        _poll_task = None
    if _bot is not None:
        try:
            if get_settings().public_base_url:
                await _bot.delete_webhook()
        except Exception:  # noqa: BLE001
            pass
        try:
            await _bot.session.close()
        except Exception:  # noqa: BLE001
            pass
    gateway.reset()
