from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AiMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AiChatForm(BaseModel):
    messages: list[AiMessage] = []
    jobs: list[dict[str, Any]] = []  # context taken from the client → no DB hit
    lang: str = "ua"
    brand: str = "Konstanta"
