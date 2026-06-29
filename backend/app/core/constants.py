"""Domain constants and small pure helpers shared across services."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

# Canonical candidate-site keys. A job's ``sites`` holds a subset; empty = everywhere.
KNOWN_SITES: tuple[str, ...] = ("konstanta", "robota")

# Supported notification/UI languages.
LANGS: tuple[str, ...] = ("ua", "cz", "en")

# Public URLs per candidate site (used to build job-alert deep links).
SITE_URLS: dict[str, str] = {
    "konstanta": "https://www.konstanta-agency.cz",
    "robota": "https://www.konstanta-agency.online",
}

# Default categories seeded on a fresh DB: (id, label_ua, label_cz, label_en).
DEFAULT_CATEGORIES: list[tuple[str, str, str, str]] = [
    ("Factory", "Завод", "Továrna", "Factory"),
    ("Warehouse", "Склад", "Sklad", "Warehouse"),
    ("Cleaning", "Прибирання", "Úklid", "Cleaning"),
    ("Drivers", "Водії", "Řidiči", "Drivers"),
]


def utcnow_iso() -> str:
    """Timezone-aware UTC timestamp in ISO-8601."""
    return datetime.now(UTC).isoformat()


def normalize_lang(lang: str | None) -> str:
    """Coerce any input to a supported language code, defaulting to Ukrainian."""
    return lang if lang in LANGS else "ua"


def slug(text: str) -> str:
    """Stable id from an EN label: 'Heavy Industry' → 'heavy-industry'.
    Falls back to a short random suffix when there are no ASCII letters/digits."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s or f"cat-{uuid.uuid4().hex[:8]}"


def clean_sites(values: list[str] | None) -> list[str]:
    """Keep only known site keys; drop blanks/unknowns; dedupe; preserve order."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values or []:
        key = (v or "").strip()
        if key in KNOWN_SITES and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def clean_cities(values: Any) -> list[dict[str, Any]]:
    """Normalize incoming cities (CityItem/dict list) → clean list, blanks dropped."""
    out: list[dict[str, Any]] = []
    for item in values or []:
        name = (getattr(item, "name", None) if not isinstance(item, dict) else item.get("name")) or ""
        name = str(name).strip()
        if not name:
            continue
        housing = getattr(item, "housing", None) if not isinstance(item, dict) else item.get("housing")
        out.append({"name": name, "housing": bool(housing)})
    return out


def parse_cities(raw: str | list | None) -> list[dict[str, Any]]:
    """JSON string or list → list of {'name': str, 'housing': bool}. Tolerant."""
    if not raw:
        return []
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []
    out: list[dict[str, Any]] = []
    for item in data if isinstance(data, list) else []:
        name = str((item or {}).get("name", "")).strip()
        if name:
            out.append({"name": name, "housing": bool((item or {}).get("housing", False))})
    return out
