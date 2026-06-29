"""
handlers/admin.py
-----------------
Owner-only staff provisioning via Telegram (the "hidden backdoor").

Only Telegram user IDs listed in settings.admin_ids may run /addstaff. The command
runs a tiny FSM (username → password → role) and calls the backend
`POST /admin/staff` with the X-Bot-Secret server-to-server header. This is also the
bootstrap path for the very first admin, before any staff account exists.

Security:
  • The command is SILENT for non-owners (it doesn't reveal that it exists).
  • The message containing the typed password is deleted best-effort.
  • The backend hashes the password (bcrypt) — plaintext never touches the DB.
"""

import logging

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ..config import settings

log = logging.getLogger(__name__)
router = Router(name="admin")


def _is_owner(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


async def _guard_owner(message: Message, state: FSMContext) -> bool:
    """Re-verify the caller's Telegram ID at EVERY step of the provisioning flow.
    If the ID ever fails to match an owner ID, abort the flow silently. This is
    defense-in-depth on top of the entry check in addstaff_start()."""
    if _is_owner(message.from_user.id if message.from_user else None):
        return True
    await state.clear()
    return False


class AddStaff(StatesGroup):
    username = State()
    password = State()
    role = State()


@router.message(Command("addstaff"))
async def addstaff_start(message: Message, state: FSMContext) -> None:
    if not _is_owner(message.from_user.id if message.from_user else None):
        return  # silent for non-owners — don't reveal the command exists
    if not settings.bot_provision_secret:
        await message.answer("⚠️ BOT_PROVISION_SECRET is not configured; cannot provision staff.")
        return
    await state.set_state(AddStaff.username)
    await message.answer(
        "👤 <b>Staff provisioning</b>\nEnter the <b>username</b> (or /cancelstaff to abort):",
        parse_mode="HTML",
    )


@router.message(StateFilter(AddStaff), Command("cancelstaff"))
async def addstaff_cancel(message: Message, state: FSMContext) -> None:
    if not await _guard_owner(message, state):
        return
    await state.clear()
    await message.answer("❌ Provisioning cancelled.")


@router.message(AddStaff.username, F.text)
async def addstaff_username(message: Message, state: FSMContext) -> None:
    if not await _guard_owner(message, state):
        return
    username = (message.text or "").strip()
    if len(username) < 3:
        await message.answer("⚠️ Username too short (min 3). Enter again:")
        return
    await state.update_data(username=username)
    await state.set_state(AddStaff.password)
    await message.answer("🔑 Enter the <b>password</b> (min 6 chars):", parse_mode="HTML")


@router.message(AddStaff.password, F.text)
async def addstaff_password(message: Message, state: FSMContext) -> None:
    if not await _guard_owner(message, state):
        return
    password = (message.text or "").strip()
    if len(password) < 6:
        await message.answer("⚠️ Password too short (min 6). Enter again:")
        return
    await state.update_data(password=password)
    await state.set_state(AddStaff.role)
    await message.answer("🎭 Enter the role: <code>admin</code> or <code>worker</code>", parse_mode="HTML")
    # Best-effort: scrub the plaintext password from the chat.
    try:
        await message.delete()
    except Exception:
        pass


@router.message(AddStaff.role, F.text)
async def addstaff_role(message: Message, state: FSMContext) -> None:
    if not await _guard_owner(message, state):
        return
    role = (message.text or "").strip().lower()
    if role not in ("admin", "worker"):
        await message.answer("⚠️ Role must be 'admin' or 'worker'. Enter again:")
        return
    data = await state.get_data()
    await state.clear()
    username = data.get("username")
    password = data.get("password")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.api_base_url}/admin/staff",
                json={"username": username, "password": password, "role": role},
                headers={"X-Bot-Secret": settings.bot_provision_secret or ""},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Staff <b>{username}</b> ({role}) created.", parse_mode="HTML")
                elif resp.status == 409:
                    await message.answer(f"⚠️ Username <b>{username}</b> already exists.", parse_mode="HTML")
                elif resp.status == 401:
                    await message.answer("⚠️ Provisioning rejected: bad/missing X-Bot-Secret.")
                else:
                    body = await resp.text()
                    await message.answer(f"⚠️ Failed (HTTP {resp.status}): {body[:200]}")
    except Exception as exc:
        log.exception("addstaff backend call failed: %s", exc)
        await message.answer("⚠️ Could not reach the backend. Try again later.")
