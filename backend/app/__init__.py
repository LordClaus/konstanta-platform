"""Konstanta backend — a modular monolith (FastAPI + async SQLAlchemy 2.0).

Layering (outer depends on inner, never the reverse):

    routers/   →  HTTP transport (thin: parse, authorize, delegate)
    services/  →  business logic (no FastAPI types leak in here)
    models/    →  SQLAlchemy ORM (persistence)
    core/ db/  →  cross-cutting infrastructure (auth, cache, sessions)

See ARCHITECTURE.md for the full picture.
"""

__version__ = "1.0.0"
