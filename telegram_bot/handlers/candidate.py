"""
handlers/candidate.py
---------------------
All candidate-facing interactions:
  • /start  → main menu
  • View Jobs → fetches & renders active jobs from the API
  • Leave Application → 4-step FSM wizard:
        Step 1: Full Name
        Step 2: Phone (contact share OR manual text)
        Step 3: Profession (InlineKeyboardMarkup built dynamically from /jobs)
        Step 4: Comment (text input OR inline "Skip ➡️" button)
"""

import asyncio
import html
import logging
import os
from typing import Optional

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    Contact,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.exceptions import TelegramBadRequest

from ..config import settings

log = logging.getLogger(__name__)
router = Router(name="candidate")

# ── Fallback profession list (used when /jobs API is unreachable) ─────────────
_PROFESSION_FALLBACK: list[tuple[str, str]] = [
    ("🚚 Driver",            "Driver"),
    ("📦 Warehouse Worker",  "Warehouse"),
    ("🏗️ Construction",      "Construction"),
    ("🧹 Cleaning Staff",    "Cleaning"),
    ("🏭 Factory Worker",    "Factory"),
    ("📋 Other",             "Other"),
]

# ── FSM States ────────────────────────────────────────────────────────────────
class ApplicationForm(StatesGroup):
    waiting_for_name       = State()
    waiting_for_phone      = State()
    waiting_for_profession = State()
    waiting_for_comment    = State()


class AiChat(StatesGroup):
    active = State()


# ── AI assistant (Gemini) — bot side. Calls Gemini directly (the key is already
# on the server, so it stays secret). Enabled only when GEMINI_API_KEY is set. ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()


def _map_lang(code: Optional[str]) -> str:
    """Telegram language_code → our notification language (ua/cz/en)."""
    c = (code or "").lower()
    if c.startswith("uk"):
        return "ua"
    if c.startswith("cs"):
        return "cz"
    if c.startswith("en"):
        return "en"
    return "ua"   # primary audience is Ukrainian-speaking


# ── Main menu keyboard ────────────────────────────────────────────────────────
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🔍 View Active Jobs")],
        [KeyboardButton(text="📝 Submit Application")],
        [KeyboardButton(text="🔔 Job Alerts")],
        [KeyboardButton(text="ℹ️ About Us")],
    ]
    if GEMINI_API_KEY:
        keyboard.append([KeyboardButton(text="💬 Assistant")])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Share Contact", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def build_profession_keyboard() -> InlineKeyboardMarkup:
    """
    Attempt to fetch active job categories from the backend.
    Falls back to a hardcoded list if the API is unreachable.
    Returns an InlineKeyboardMarkup with one button per category.
    """
    rows: list[list[InlineKeyboardButton]] = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.api_base_url}/jobs",
                timeout=aiohttp.ClientTimeout(total=6),
            ) as resp:
                resp.raise_for_status()
                jobs: list[dict] = await resp.json()

        # Extract unique job types preserving insertion order.
        # `type` is the canonical filter field; fall back to the legacy `category` alias.
        seen: set[str] = set()
        categories: list[str] = []
        for job in jobs:
            cat = ((job.get("type") or job.get("category")) or "").strip()
            if cat and cat not in seen:
                seen.add(cat)
                categories.append(cat)

        # Emoji map for known categories
        EMOJI: dict[str, str] = {
            "Drivers":   "🚚",
            "Warehouse": "📦",
            "Factory":   "🏭",
            "Cleaning":  "🧹",
            "Construction": "🏗️",
        }

        for cat in categories:
            emoji = EMOJI.get(cat, "💼")
            rows.append([
                InlineKeyboardButton(
                    text=f"{emoji} {cat}",
                    callback_data=f"profession:{cat}",
                )
            ])

        # Always append "Other" if not already present
        if "Other" not in seen:
            rows.append([InlineKeyboardButton(text="📋 Other", callback_data="profession:Other")])

        log.info("Built dynamic profession keyboard with %d categories.", len(rows))

    except aiohttp.ClientError as exc:
        log.warning("Could not fetch jobs for profession keyboard (%s). Using fallback.", exc)
        rows = [
            [InlineKeyboardButton(text=label, callback_data=f"profession:{value}")]
            for label, value in _PROFESSION_FALLBACK
        ]
    except (asyncio.TimeoutError, Exception) as exc:
        # Catch asyncio.TimeoutError (not a subclass of ClientError in Python 3.11+)
        # and other unexpected errors to prevent handler crash
        log.warning("Timeout or error fetching jobs for profession keyboard (%s). Using fallback.", exc)
        rows = [
            [InlineKeyboardButton(text=label, callback_data=f"profession:{value}")]
            for label, value in _PROFESSION_FALLBACK
        ]

    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Skip ➡️", callback_data="comment:skip")
        ]]
    )


# ── /start ────────────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    first_name = (message.from_user.first_name or "there").strip()

    await message.answer(
        f"👋 Привіт / Hello, <b>{first_name}</b>!\n\n"
        "Welcome to <b>Konstanta Recruitment</b> — your bridge to great jobs in Europe.\n\n"
        "🇺🇦 Ми допомагаємо знайти роботу в Чехії та по всій Європі.\n"
        "🇨🇿 Pomáháme najít práci v České republice a celé Evropě.\n\n"
        "Use the menu below to get started:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


# ── /cancel ──────────────────────────────────────────────────────────────────
# Registered BEFORE the FSM text-step handlers so it is never shadowed by them
# (W7). Uses the Command filter and no state filter → works from any state.
@router.message(Command("cancel"))
async def cancel_fsm(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current:
        await message.answer(
            "❌ Application cancelled.\n\nYou can start a new one anytime.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(
            "Nothing to cancel. Use the menu to get started.",
            reply_markup=main_menu_keyboard(),
        )


# ── About Us ──────────────────────────────────────────────────────────────────
@router.message(F.text == "ℹ️ About Us")
async def about_us(message: Message) -> None:
    await message.answer(
        "🏢 <b>Konstanta s.r.o.</b>\n\n"
        "We are a professional recruitment agency with <b>16+ years</b> on the market, "
        "connecting talented workers with leading employers across Europe.\n\n"
        "📍 <b>Headquarters:</b> Opletalova 921/6, 110 00 Praha 1\n"
        "📞 <b>Phone:</b> +380 800 100 59\n"
        "👥 <b>1850+ workers</b> placed &nbsp;·&nbsp; <b>70+ permanent clients</b>\n\n"
        "Our team works around the clock to match candidates with the right opportunities.",
        parse_mode="HTML",
    )


# ── Job Alerts (subscribe / unsubscribe) ─────────────────────────────────────
async def _post_subscribe(chat_id: int, lang: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.api_base_url}/subscribe",
                json={"telegram_chat_id": chat_id, "lang": lang},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                return resp.status < 300
    except Exception as exc:  # noqa: BLE001
        log.warning("subscribe failed: %s", exc)
        return False


async def _post_unsubscribe(chat_id: int) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.api_base_url}/unsubscribe",
                json={"telegram_chat_id": chat_id},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                return resp.status < 300
    except Exception as exc:  # noqa: BLE001
        log.warning("unsubscribe failed: %s", exc)
        return False


@router.message(F.text == "🔔 Job Alerts")
async def alerts_on(message: Message) -> None:
    lang = _map_lang(message.from_user.language_code if message.from_user else None)
    ok = await _post_subscribe(message.chat.id, lang)
    if ok:
        await message.answer(
            "🔔 <b>Job alerts are on.</b>\n\n"
            "We'll message you here whenever a new vacancy is posted.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔕 Turn off alerts", callback_data="alerts:off")
            ]]),
            parse_mode="HTML",
        )
    else:
        await message.answer("⚠️ Couldn't enable alerts right now. Please try again later.")


@router.callback_query(F.data == "alerts:off")
async def alerts_off(callback: CallbackQuery) -> None:
    await callback.answer()
    ok = await _post_unsubscribe(callback.message.chat.id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as exc:
        log.warning("alerts_off edit_reply_markup failed: %s", exc)
    await callback.message.answer(
        "🔕 Job alerts turned off." if ok else "⚠️ Couldn't turn off alerts. Please try again."
    )


# ── View Active Jobs ──────────────────────────────────────────────────────────
@router.message(F.text == "🔍 View Active Jobs")
async def view_jobs(message: Message) -> None:
    await message.answer("🔄 Fetching active positions…")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.api_base_url}/jobs",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                jobs: list[dict] = await resp.json()

    except aiohttp.ClientError as exc:
        log.error("Failed to fetch jobs: %s", exc)
        await message.answer(
            "⚠️ <b>Server is temporarily unavailable.</b>\n"
            "Could not load job listings right now. Please try again in a few minutes.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        return
    except (asyncio.TimeoutError, Exception) as exc:
        # Catch asyncio.TimeoutError and other errors to prevent handler crash
        log.error("Timeout or error fetching jobs: %s", exc)
        await message.answer(
            "⚠️ <b>Server is temporarily unavailable.</b>\n"
            "Could not load job listings right now. Please try again in a few minutes.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        return

    if not jobs:
        await message.answer(
            "😔 No open positions at the moment.\nCheck back soon — new jobs are added regularly!",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Send up to 10 jobs as individual cards
    display_jobs = jobs[:10]
    for job in display_jobs:
        title_obj = job.get("title") or {}
        title = (
            title_obj.get("ua")
            or title_obj.get("en")
            or title_obj.get("cz")
            or job.get("title")
            or "Unknown position"
        )
        category = job.get("type") or job.get("category") or "—"
        location = job.get("location") or "—"
        job_id   = job.get("id") or "—"
        is_new   = job.get("new", False)

        badge = "🆕 " if is_new else "📌 "
        text = (
            f"{badge}<b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📂 <b>Category:</b> {category}\n"
            f"📍 <b>Location:</b> {location}\n"
            f"🆔 <b>ID:</b> <code>{job_id}</code>"
        )
        await message.answer(text, parse_mode="HTML")

    if len(jobs) > 10:
        await message.answer(
            f"…and <b>{len(jobs) - 10}</b> more positions available.\n"
            "Contact us directly for the full list.",
            parse_mode="HTML",
        )

    await message.answer(
        "👇 Interested in a position? Use the button below to submit your application.",
        reply_markup=main_menu_keyboard(),
    )


# ── FSM: Submit Application ───────────────────────────────────────────────────

@router.message(F.text == "📝 Submit Application")
async def apply_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ApplicationForm.waiting_for_name)
    # Remember the user's language now (the real user message) for status notifications.
    await state.update_data(lang=_map_lang(message.from_user.language_code if message.from_user else None))
    await message.answer(
        "📋 <b>Application Form</b>\n\n"
        "I'll ask you a few quick questions. You can type <code>/cancel</code> at any time to stop.\n\n"
        "<b>Step 1 / 4</b> — Please enter your <b>full name</b>:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )


# ── Step 1: Name ──────────────────────────────────────────────────────────────
@router.message(ApplicationForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("⚠️ Please send your name as a text message.")
        return

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ Name is too short. Please enter your full name (first and last):")
        return

    await state.update_data(name=name)
    await state.set_state(ApplicationForm.waiting_for_phone)
    await message.answer(
        f"✅ Got it, <b>{name}</b>!\n\n"
        "<b>Step 2 / 4</b> — Please share your <b>phone number</b>.\n\n"
        "Tap the button below to share your contact, or type your number manually "
        "(e.g. <code>+380501234567</code>):",
        reply_markup=phone_request_keyboard(),
        parse_mode="HTML",
    )


# ── Step 2: Phone (contact button) ────────────────────────────────────────────
@router.message(ApplicationForm.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    contact: Contact = message.contact
    phone = contact.phone_number or ""
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone_proceed(message, state, phone)


# ── Step 2: Phone (manual text) ───────────────────────────────────────────────
@router.message(ApplicationForm.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) < 7:
        await message.answer(
            "⚠️ That doesn't look like a valid phone number.\n"
            "Please enter at least 7 digits (e.g. <code>+380501234567</code>):",
            parse_mode="HTML",
        )
        return
    await _save_phone_proceed(message, state, raw)


async def _save_phone_proceed(message: Message, state: FSMContext, phone: str) -> None:
    await state.update_data(phone=phone)
    await state.set_state(ApplicationForm.waiting_for_profession)

    keyboard = await build_profession_keyboard()

    await message.answer(
        "✅ Phone saved!\n\n"
        "<b>Step 3 / 4</b> — Select your <b>desired profession</b> or job category:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await message.answer("👇 Choose one:", reply_markup=keyboard)


# ── Step 3: Profession (inline callback) ──────────────────────────────────────
@router.callback_query(F.data.startswith("profession:"), ApplicationForm.waiting_for_profession)
async def process_profession(callback: CallbackQuery, state: FSMContext) -> None:
    # Answer callback immediately to dismiss loading spinner before network operations
    await callback.answer()

    profession = callback.data.split(":", 1)[1].strip()
    await state.update_data(profession=profession)
    await state.set_state(ApplicationForm.waiting_for_comment)

    # Remove inline keyboard from profession message
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"✅ Profession: <b>{html.escape(profession)}</b>\n\n"
        "<b>Step 4 / 4</b> — Would you like to add a <b>brief comment</b>?\n\n"
        "You can describe your experience, preferred work location, availability, "
        "or anything else that might help us find the right position for you.\n\n"
        "Or tap <b>Skip ➡️</b> to submit your application right away.",
        reply_markup=skip_comment_keyboard(),
        parse_mode="HTML",
    )


# ── Catch-all: profession callbacks when FSM state is not waiting_for_profession ──────
@router.callback_query(F.data.startswith("profession:"))
async def profession_callback_stale_state(callback: CallbackQuery) -> None:
    # This handler matches profession: callbacks but state is not waiting_for_profession
    # (user tapped button again after state changed)
    # Answer the callback to dismiss the loading spinner
    await callback.answer(
        "Profession selection is no longer available. Please start again.",
        show_alert=False,
    )


# ── Step 4: Comment (text input) ─────────────────────────────────────────────
@router.message(ApplicationForm.waiting_for_comment, F.text)
async def process_comment_text(message: Message, state: FSMContext) -> None:
    comment = message.text.strip() if message.text else ""

    if len(comment) > 1000:
        await message.answer("⚠️ Comment is too long (max 1000 characters). Please shorten it:")
        return

    await state.update_data(comment=comment)
    await _submit_application(message, state)


# ── Step 4: Skip comment ──────────────────────────────────────────────────────
@router.callback_query(F.data == "comment:skip", ApplicationForm.waiting_for_comment)
async def process_comment_skip(callback: CallbackQuery, state: FSMContext) -> None:
    # Answer callback immediately to dismiss loading spinner before network operations
    await callback.answer()

    await state.update_data(comment=None)

    # Guard edit_reply_markup against TelegramBadRequest (message too old, already edited, etc.)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as exc:
        log.warning("Could not edit reply markup on comment skip (message too old?): %s", exc)

    await _submit_application(callback.message, state)


# ── Final submission ──────────────────────────────────────────────────────────
async def _submit_application(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    payload = {
        "name":       data.get("name", ""),
        "phone":      data.get("phone", ""),
        "profession": data.get("profession") or None,
        "comment":    data.get("comment")    or None,
        "platform":   "telegram",
        "telegram_chat_id": message.chat.id,   # enables Telegram status updates
        "lang":       data.get("lang") or "ua",
    }

    # Validate payload before submission to catch race conditions like /cancel clearing state
    if not payload["name"] or not payload["phone"]:
        await message.answer(
            "⚠️ <b>Application incomplete.</b>\n\n"
            "Your application data was lost (possibly due to a timeout or if you used /cancel). "
            "Please start a new application to try again.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    sending_msg = await message.answer("⏳ Submitting your application…")

    success = await _post_application(payload)

    # Try to delete the "Submitting…" message (best-effort, ignore if fails)
    try:
        await sending_msg.delete()
    except Exception:
        pass

    if success:
        await message.answer(
            "🎉 <b>Application submitted successfully!</b>\n\n"
            f"📌 <b>Name:</b> {html.escape(payload['name'])}\n"
            f"📞 <b>Phone:</b> {html.escape(payload['phone'])}\n"
            f"💼 <b>Profession:</b> {html.escape(payload.get('profession') or '—')}\n"
            f"💬 <b>Comment:</b> {html.escape(payload.get('comment') or '—')}\n\n"
            "Our managers will review your application and contact you shortly. "
            "Thank you for choosing <b>Konstanta Recruitment</b>! 🚀",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        log.info(
            "Application submitted: name=%s phone=%s profession=%s",
            payload["name"], payload["phone"], payload.get("profession"),
        )
    else:
        await message.answer(
            "⚠️ <b>Server is temporarily unavailable.</b>\n\n"
            "We couldn't save your application right now. Please try again in a few minutes "
            "or contact us directly at <b>+380 800 100 59</b>.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )


async def _post_application(payload: dict) -> bool:
    """POST the application payload to the FastAPI backend. Returns True on success."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.api_base_url}/apply",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                return True
    except aiohttp.ClientError as exc:
        log.error("Failed to POST /apply: %s", exc)
        return False
    except Exception as exc:
        log.exception("Unexpected error posting application: %s", exc)
        return False


# ── AI assistant (opt-in mode) ────────────────────────────────────────────────
def assistant_exit_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Menu")]],
        resize_keyboard=True,
    )


async def _fetch_jobs_block() -> str:
    """Compact active-vacancies summary for the AI context (one /jobs GET per session)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.api_base_url}/jobs",
                timeout=aiohttp.ClientTimeout(total=6),
            ) as resp:
                resp.raise_for_status()
                jobs = await resp.json()
    except Exception as exc:  # noqa: BLE001 — context is optional, never fail the chat
        log.warning("AI: could not fetch jobs context (%s).", exc)
        return ""

    lines: list[str] = []
    for job in (jobs or [])[:40]:
        title_obj = job.get("title") or {}
        title = title_obj.get("ua") or title_obj.get("cz") or title_obj.get("en") or ""
        if not title:
            continue
        parts = [title]
        if job.get("type") or job.get("category"):
            parts.append(f"[{job.get('type') or job.get('category')}]")
        if job.get("location"):
            parts.append(str(job.get("location")))
        if job.get("salary"):
            parts.append(str(job.get("salary")))
        lines.append("- " + " ".join(parts))
    return "\n".join(lines)


async def _ask_ai(history: list[dict], jobs_block: str) -> str:
    """Forward the short conversation to Gemini. Returns plain text (no HTML)."""
    system = (
        "You are a friendly assistant of the recruitment agency Konstanta (official employment "
        "in the Czech Republic: factory, warehouse, cleaning, drivers). Answer concisely in the "
        "same language as the user (Ukrainian, Czech or English). Help pick a vacancy, explain the "
        "application process, housing, pay and documents. Services are free for candidates. Do not "
        "invent vacancies that are not in the list. If unsure, suggest tapping 'Submit Application' "
        "or contacting a manager.\n\nActive vacancies:\n" + (jobs_block or "(none provided)")
    )
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"][:2000]}]}
        for m in history[-12:]
    ]
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 600, "temperature": 0.4},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    log.warning("Gemini(bot) error %s: %s", resp.status, str(data)[:200])
                    return "Sorry, I couldn't answer right now. Please try again or contact us."
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini(bot) call failed: %s", exc)
        return "Sorry, the assistant is temporarily unavailable. Please try later."

    try:
        return (data["candidates"][0]["content"]["parts"][0]["text"] or "").strip() or "…"
    except (KeyError, IndexError, TypeError):
        return "Sorry, I couldn't answer. Please rephrase your question."


@router.message(F.text == "💬 Assistant")
async def assistant_start(message: Message, state: FSMContext) -> None:
    if not GEMINI_API_KEY:
        await message.answer(
            "ℹ️ The assistant is not available right now. Use the menu to view jobs or apply.",
            reply_markup=main_menu_keyboard(),
        )
        return
    jobs_block = await _fetch_jobs_block()
    await state.set_state(AiChat.active)
    await state.update_data(ai_history=[], ai_jobs=jobs_block)
    await message.answer(
        "💬 <b>Assistant</b>\n\n"
        "Ask me anything about our jobs, the application process, housing or pay — "
        "in 🇺🇦 Ukrainian, 🇨🇿 Czech or 🇬🇧 English.\n\n"
        "Tap <b>⬅️ Menu</b> to exit.",
        reply_markup=assistant_exit_keyboard(),
        parse_mode="HTML",
    )


@router.message(AiChat.active, F.text)
async def assistant_chat(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text in ("⬅️ Menu", "Menu", "/cancel"):
        await state.clear()
        await message.answer("👍 Back to the menu.", reply_markup=main_menu_keyboard())
        return
    if not text:
        return

    data = await state.get_data()
    history: list[dict] = data.get("ai_history", [])
    jobs_block: str = data.get("ai_jobs", "")
    history.append({"role": "user", "content": text})

    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
    except Exception:  # noqa: BLE001
        pass

    reply = await _ask_ai(history, jobs_block)
    history.append({"role": "assistant", "content": reply})
    await state.update_data(ai_history=history[-12:])
    # Plain text (no parse_mode) so model output never breaks Telegram HTML parsing.
    await message.answer(reply, reply_markup=assistant_exit_keyboard())
