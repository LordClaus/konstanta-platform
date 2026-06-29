from __future__ import annotations

from pydantic import BaseModel


class ApplicationForm(BaseModel):
    name: str
    phone: str
    email: str | None = None
    profession: str | None = None
    comment: str | None = None
    platform: str = "website"  # "website" | "telegram"
    telegram_chat_id: int | None = None  # set by the bot → enables Telegram updates
    lang: str | None = None  # ua/cz/en → language of status notifications
