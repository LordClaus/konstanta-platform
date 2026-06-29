from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Category(Base, TimestampMixin):
    """An admin-managed job category. ``id`` is a stable slug derived from the EN
    label; jobs reference it via ``Job.type``. Labels drive the candidate sites'
    filter buttons and captions in three languages."""

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label_ua: Mapped[str | None] = mapped_column(String(128))
    label_cz: Mapped[str | None] = mapped_column(String(128))
    label_en: Mapped[str | None] = mapped_column(String(128))
