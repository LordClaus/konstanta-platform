"""AI assistant orchestration: prompt assembly + provider dispatch.

Kept deliberately light on the bottleneck server: the jobs context comes from the
client (no DB hit), input is capped, and the upstream call is time-boxed inside
the provider. The vendor is chosen by :func:`get_provider`.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.constants import normalize_lang
from app.schemas.ai import AiChatForm
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_provider

_SYSTEM = {
    "ua": (
        "Ти — доброзичливий помічник кадрової агенції {brand} (офіційне працевлаштування "
        "в Чехії: завод, склад, прибирання, водії). Відповідай стисло й по суті, тією ж мовою, "
        "що й користувач. Допомагай із вибором вакансії, поясни процес подачі анкети, житло, "
        "оплату, документи. Послуги для кандидата безкоштовні. Не вигадуй вакансій, яких немає "
        "у списку нижче. Якщо не знаєш — запропонуй подати анкету на сайті або звернутися до менеджера."
    ),
    "cz": (
        "Jsi přátelský asistent personální agentury {brand} (oficiální zaměstnání v ČR: výroba, "
        "sklad, úklid, doprava). Odpovídej stručně a věcně, stejným jazykem jako uživatel. Pomáhej "
        "s výběrem pozice, vysvětli proces přihlášky, ubytování, mzdu, dokumenty. Služby jsou pro "
        "uchazeče zdarma. Nevymýšlej pozice, které nejsou v seznamu níže. Když nevíš — navrhni "
        "podání přihlášky na webu nebo kontakt na konzultanta."
    ),
    "en": (
        "You are a friendly assistant of the recruitment agency {brand} (official employment in "
        "the Czech Republic: factory, warehouse, cleaning, drivers). Answer concisely and to the "
        "point, in the same language as the user. Help pick a vacancy, explain the application "
        "process, housing, pay, documents. Services are free for candidates. Do not invent "
        "vacancies that are not in the list below. If unsure, suggest applying on the site or "
        "contacting a consultant."
    ),
}

_FALLBACK = {
    "ua": "Вибачте, зараз не вдалося відповісти. Спробуйте перефразувати або зв'яжіться з нами.",
    "cz": "Omlouvám se, teď se nepodařilo odpovědět. Zkuste to jinak nebo nás kontaktujte.",
    "en": "Sorry, I couldn't answer right now. Please rephrase or contact us.",
}


def _jobs_block(jobs: list[dict]) -> str:
    lines: list[str] = []
    for j in jobs[:40]:
        title = str(j.get("title") or "").strip()
        if not title:
            continue
        parts = [title]
        if j.get("type"):
            parts.append(f"[{j.get('type')}]")
        if j.get("location"):
            parts.append(str(j.get("location")))
        if j.get("salary"):
            parts.append(str(j.get("salary")))
        lines.append("- " + " · ".join(parts))
    return "\n".join(lines) if lines else "(no active vacancies provided)"


def build_system_prompt(form: AiChatForm, lang: str) -> str:
    brand = (form.brand or "Konstanta")[:60]
    return _SYSTEM[lang].format(brand=brand) + "\n\nActive vacancies:\n" + _jobs_block(form.jobs)


async def chat(form: AiChatForm) -> str:
    provider = get_provider()
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI assistant is not configured")

    lang = normalize_lang(form.lang)
    messages = [m for m in form.messages if m.content and m.content.strip()][-12:]
    if not messages:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No messages")

    system = build_system_prompt(form, lang)
    try:
        reply = await provider.complete(system, messages)
    except AIProviderError as exc:
        detail = str(exc)
        if detail == "timeout":
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "AI service timeout") from exc
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI service error") from exc
    return reply or _FALLBACK[lang]
