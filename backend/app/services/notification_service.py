"""Candidate notifications + job-alert fan-out (Telegram + Email via Brevo).

Everything here is best-effort and fire-and-forget so the request paths (/apply,
the manager WS actions, POST /jobs) stay snappy. Background tasks own their own DB
session because the request session is already closed by the time they run.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from typing import Any

import aiohttp
from sqlalchemy import select

from app.config import get_settings
from app.core.constants import SITE_URLS, normalize_lang
from app.db.session import get_sessionmaker
from app.models import Subscription
from app.services.telegram_gateway import gateway

log = logging.getLogger("api.notify")

# Strong refs so fire-and-forget tasks aren't garbage-collected mid-flight.
_tasks: set[asyncio.Task] = set()

# Friendly localized copy per candidate-facing stage.
_CAND_MSG = {
    "received": {
        "ua": ("Заявку отримано", "Дякуємо! Ми отримали вашу заявку та зв'яжемося з вами найближчим часом."),
        "cz": ("Přihláška přijata", "Děkujeme! Vaši přihlášku jsme přijali a brzy se vám ozveme."),
        "en": ("Application received", "Thank you! We have received your application and will contact you soon."),
    },
    "reviewing": {
        "ua": ("Заявку розглядають", "Вашу заявку взяв у роботу менеджер. Незабаром ми з вами зв'яжемося."),
        "cz": ("Přihláška se zpracovává", "Vaši přihlášku převzal konzultant. Brzy se vám ozveme."),
        "en": ("Application in review", "A consultant is now reviewing your application. We'll be in touch soon."),
    },
    "processed": {
        "ua": ("Заявку опрацьовано", "Вашу заявку опрацьовано. Менеджер зв'яжеться з вами щодо подальших кроків."),
        "cz": ("Přihláška vyřízena", "Vaši přihlášku jsme vyřídili. Konzultant vás bude kontaktovat ohledně dalších kroků."),
        "en": ("Application processed", "Your application has been processed. A consultant will contact you about next steps."),
    },
}

_ALERT_MSG = {
    "ua": ("Нова вакансія", "З'явилася нова вакансія, яка може вас зацікавити:", "Дивитися вакансію", "Відписатися"),
    "cz": ("Nová pozice", "Objevila se nová pozice, která by vás mohla zajímat:", "Zobrazit pozici", "Odhlásit se"),
    "en": ("New vacancy", "A new vacancy you might be interested in:", "View vacancy", "Unsubscribe"),
}


def unsub_sig(email: str) -> str:
    secret = (get_settings().jwt_secret or "change-me").encode()
    return hmac.new(secret, email.lower().encode(), hashlib.sha256).hexdigest()[:16]


async def send_email(to: str, subject: str, html: str) -> None:
    s = get_settings()
    if not (s.brevo_api_key and s.mail_from and to):
        return
    payload = {
        "sender": {"name": s.mail_from_name, "email": s.mail_from},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": s.brevo_api_key, "Content-Type": "application/json", "accept": "application/json"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 300:
                    log.warning("Brevo email %s: %s", resp.status, (await resp.text())[:200])
    except Exception as exc:  # noqa: BLE001
        log.warning("Brevo email failed: %s", exc)


async def _notify_candidate(email, chat_id, lang, stage: str) -> None:
    msgs = _CAND_MSG.get(stage)
    if not msgs:
        return
    lng = normalize_lang(lang)
    subject, body = msgs[lng]
    brand = get_settings().mail_from_name or "Konstanta"
    if email:
        html = (
            "<div style='font-family:sans-serif;font-size:15px;color:#1a2b4b'>"
            f"<p>{body}</p>"
            f"<p style='color:#64748b;font-size:13px'>— {brand}</p></div>"
        )
        await send_email(email, subject, html)
    if chat_id:
        await gateway.send_message(chat_id, f"✅ {subject}\n\n{body}")


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def notify_candidate(email, chat_id, lang, stage: str) -> None:
    """Fire-and-forget candidate notification."""
    if not (email or chat_id):
        return
    _spawn(_notify_candidate(email, chat_id, lang, stage))


async def _fanout_job_alert(job: dict[str, Any]) -> None:
    """Notify every matching subscriber about a new vacancy (email + Telegram)."""
    try:
        async with get_sessionmaker()() as session:
            subs = (await session.execute(select(Subscription))).scalars().all()
    except Exception as exc:  # noqa: BLE001
        log.warning("job alert: could not load subscriptions: %s", exc)
        return

    public_base = get_settings().public_base_url
    job_sites = job.get("sites") or []  # [] = everywhere
    job_type = job.get("type") or ""
    for sub in subs:
        if sub.category and sub.category != job_type:
            continue
        if sub.site and job_sites and sub.site not in job_sites:
            continue
        lng = normalize_lang(sub.lang)
        title = (job.get("title") or {}).get(lng) or (job.get("title") or {}).get("cz") or ""
        if not title:
            continue
        detail = " · ".join([p for p in (job.get("location") or "", job.get("salary") or "") if p])
        subj, intro, cta, unsub = _ALERT_MSG[lng]
        link_site = sub.site or (job_sites[0] if job_sites else "robota")
        base = SITE_URLS.get(link_site, SITE_URLS["robota"])
        url = f"{base}/#job-{job.get('id')}"
        if sub.email:
            unsub_html = ""
            if public_base:
                unsub_url = f"{public_base}/unsubscribe?e={sub.email}&k={unsub_sig(sub.email)}"
                unsub_html = (
                    f"<p style='color:#94a3b8;font-size:12px;margin-top:20px'>"
                    f"<a href='{unsub_url}' style='color:#94a3b8'>{unsub}</a></p>"
                )
            html = (
                "<div style='font-family:sans-serif;font-size:15px;color:#1a2b4b'>"
                f"<p>{intro}</p><h3 style='margin:8px 0'>{title}</h3>"
                f"<p style='color:#475569'>{detail}</p>"
                f"<p><a href='{url}' style='color:#0891b2'>{cta} →</a></p>"
                f"{unsub_html}</div>"
            )
            await send_email(sub.email, f"{subj}: {title}", html)
        if sub.telegram_chat_id:
            tail = f"\n{detail}" if detail else ""
            await gateway.send_message(sub.telegram_chat_id, f"🆕 {subj}\n\n{title}{tail}\n{url}")


def fanout_job_alert(job: dict[str, Any]) -> None:
    """Fire-and-forget job-alert fan-out (called after a job is created)."""
    _spawn(_fanout_job_alert(job))
