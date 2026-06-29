from __future__ import annotations

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Job(Base, TimestampMixin):
    """A published vacancy.

    ``type`` is a *soft* reference to ``categories.id`` (a slug). It is kept as a
    plain column rather than a hard FK so a category can be renamed/managed
    independently and legacy values keep matching; the "category in use" guard on
    delete is enforced in the service layer. ``sites`` / ``cities`` are JSON so a
    single row carries multi-site placement and per-city housing flags.
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title_ua: Mapped[str | None] = mapped_column(String(255))
    title_cz: Mapped[str | None] = mapped_column(String(255))
    title_en: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(64), index=True)  # category id
    location: Mapped[str | None] = mapped_column(String(512))
    salary: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024))
    # list[str] of candidate-site keys; empty = "show everywhere".
    sites: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # list[{"name": str, "housing": bool}]
    cities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
