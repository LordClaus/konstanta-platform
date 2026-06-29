from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Subscription(Base, TimestampMixin):
    """A job-alert subscription (email and/or Telegram). NULL ``category`` or
    ``site`` means "match everything"."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    category: Mapped[str | None] = mapped_column(String(64))
    site: Mapped[str | None] = mapped_column(String(32))
    lang: Mapped[str | None] = mapped_column(String(8))
