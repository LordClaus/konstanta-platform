from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    """A public-site candidate account. Self-registered via email/password or
    Google. ``password_hash`` is NULL for Google-only accounts and vice versa."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    birthdate: Mapped[date | None] = mapped_column(Date)
