from __future__ import annotations

from pydantic import BaseModel


class ReviewForm(BaseModel):
    userName: str
    text: str
    createdAt: str | None = None
    site: str | None = None  # candidate site the review was left on
