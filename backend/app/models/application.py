from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Application(Base, TimestampMixin):
    """A candidate's job application (from the website form or the Telegram bot).

    Lifecycle status: ``new`` → ``processing`` (a manager claimed it) → ``completed``.
    Candidate-facing copy maps these to received / reviewing / processed.
    """

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    profession: Mapped[str | None] = mapped_column(String(255))
    comment: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(32), default="website", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False, index=True)
    manager_name: Mapped[str | None] = mapped_column(String(255), index=True)
    consent: Mapped[bool | None] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text)
    # Set by the Telegram bot so status updates can be pushed back to the chat.
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    lang: Mapped[str | None] = mapped_column(String(8))
