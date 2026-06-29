from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Review(Base, TimestampMixin):
    """A public testimonial left on a candidate site."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_name: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer)
    site: Mapped[str | None] = mapped_column(String(32))
