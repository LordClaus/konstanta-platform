from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.core import security
from app.services import application_service, telegram
from app.ws.manager import manager

router = APIRouter(tags=["realtime"])
log = logging.getLogger("api.ws")


@router.websocket("/ws/managers")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    # ── Auth handshake: first frame must carry a staff JWT or the bot secret ──
    try:
        first = json.loads(await websocket.receive_text())
    except (WebSocketDisconnect, json.JSONDecodeError):
        await websocket.close(code=1008)
        return

    authed = False
    ws_username = None  # server-verified (never trusted from message bodies)
    if first.get("action") == "auth":
        token = first.get("token")
        bot_secret = first.get("bot_secret")
        provision_secret = get_settings().bot_provision_secret
        if token:
            try:
                payload = security.decode_token(token)
                if payload.get("scope") == "staff":
                    authed = True
                    ws_username = payload.get("username") or str(payload.get("sub") or "")
            except HTTPException:
                authed = False
        elif bot_secret and provision_secret and bot_secret == provision_secret:
            authed = True
    if not authed:
        try:
            await websocket.send_json({"action": "error", "message": "Authentication required"})
        except Exception:  # noqa: BLE001
            pass
        await websocket.close(code=1008)
        return

    manager.add(websocket)
    try:
        await websocket.send_json({"action": "auth_ok"})
        while True:
            msg = json.loads(await websocket.receive_text())
            action = msg.get("action")

            if action == "lock_ticket":
                app_id = msg.get("application_id")
                manager_name = ws_username or msg.get("manager_name")
                if not manager_name:
                    await websocket.send_json({
                        "action": "error", "application_id": app_id,
                        "message": "manager_name is required",
                    })
                    continue
                ok, message = await application_service.perform_lock(app_id, manager_name)
                if not ok:
                    await websocket.send_json({
                        "action": "error", "application_id": app_id,
                        "manager_name": manager_name, "message": message,
                    })

            elif action == "complete_ticket":
                app_id = msg.get("application_id")
                ok, message = await application_service.perform_complete(app_id, ws_username)
                if not ok:
                    await websocket.send_json({
                        "action": "error", "application_id": app_id, "message": message,
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:  # noqa: BLE001
        log.error("WebSocket error: %s", exc)
        manager.disconnect(websocket)


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram updates (webhook mode) and feed them to the in-process
    dispatcher. Protected by the secret_token Telegram echoes back."""
    bot, dp = telegram.get_bot(), telegram.get_dispatcher()
    if dp is None or bot is None:
        raise HTTPException(status_code=503, detail="Bot not enabled")
    provision_secret = get_settings().bot_provision_secret
    if provision_secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != provision_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    from aiogram.types import Update

    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
    except Exception as exc:  # noqa: BLE001
        log.warning("Invalid Telegram update payload: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid update") from exc
    # ACK immediately; process in the background so a slow handler never blows
    # Telegram's webhook timeout. Keep a strong ref so the task isn't GC'd.
    import asyncio

    task = asyncio.create_task(dp.feed_update(bot, update))
    _webhook_tasks.add(task)
    task.add_done_callback(_webhook_tasks.discard)
    return {"ok": True}


_webhook_tasks: set = set()
