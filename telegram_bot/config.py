"""
config.py
---------
Centralised configuration loaded from environment variables (or a .env file).
All other modules import from here — never read os.getenv() directly elsewhere.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Anchor .env to this file's directory (not the process CWD) so the bot finds its
# config on Serv00/FreeBSD regardless of how the process is launched. Absent file =>
# no-op, and real environment variables take over.
load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class Settings:
    # ── Telegram ──────────────────────────────────────────────────────────────
    bot_token: str
    """Telegram Bot API token from @BotFather."""

    manager_group_id: int
    """
    Telegram chat_id of the managers' group (negative number for supergroups).
    Example: -1001234567890
    """

    admin_ids: list[int]
    """
    Optional list of individual admin user IDs who can receive alerts
    in addition to (or instead of) the group.
    """

    # ── FastAPI backend ───────────────────────────────────────────────────────
    api_base_url: str
    """Base URL of the FastAPI service.  e.g. http://localhost:8000"""

    ws_url: str
    """WebSocket endpoint for the managers' hub.  e.g. ws://localhost:8000/ws/managers"""

    bot_provision_secret: str | None = None
    """Server-to-server secret. Sent as X-Bot-Secret to POST /admin/staff (staff
    provisioning) and as the WebSocket `bot_secret` auth handshake. Must match the
    backend's BOT_PROVISION_SECRET."""

    # ── Behaviour ─────────────────────────────────────────────────────────────
    ws_reconnect_delay: float = 5.0
    """Seconds to wait before reconnecting to the WebSocket after a disconnect."""


def _parse_admin_ids(raw: str | None) -> list[int]:
    """Parse a comma-separated string of Telegram user IDs into a list of ints."""
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise EnvironmentError("BOT_TOKEN is not set in the environment.")

    manager_group_id_raw = os.getenv("MANAGER_GROUP_ID")
    if not manager_group_id_raw:
        raise EnvironmentError("MANAGER_GROUP_ID is not set in the environment.")

    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    ws_url = os.getenv("WS_URL", api_base_url.replace("http", "ws") + "/ws/managers")

    return Settings(
        bot_token=bot_token,
        manager_group_id=int(manager_group_id_raw),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
        api_base_url=api_base_url,
        ws_url=ws_url,
        bot_provision_secret=os.getenv("BOT_PROVISION_SECRET"),
        ws_reconnect_delay=float(os.getenv("WS_RECONNECT_DELAY", "5.0")),
    )


# Module-level singleton — import `settings` everywhere else.
settings: Settings = load_settings()
