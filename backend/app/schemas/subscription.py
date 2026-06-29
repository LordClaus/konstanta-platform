from __future__ import annotations

from pydantic import BaseModel


class SubscribeForm(BaseModel):
    email: str | None = None
    telegram_chat_id: int | None = None
    category: str | None = None
    site: str | None = None
    lang: str | None = None


class UnsubscribeForm(BaseModel):
    email: str | None = None
    telegram_chat_id: int | None = None
