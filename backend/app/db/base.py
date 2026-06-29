"""Declarative base shared by every ORM model.

Importing `Base` (and, via app.models, every model) is what populates
`Base.metadata` — Alembic autogenerate and the test-suite's create_all both
rely on that metadata being fully loaded.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy 2.0 declarative base."""
