"""Application entry point — the FastAPI app factory and process lifespan.

`create_app()` assembles the modular monolith: middleware, the rate limiter, and
every domain router. The lifespan handler initializes the DB layer, seeds default
data, warms the read cache, and starts the optional in-process Telegram bot.

Run locally:  ``uvicorn app.main:app --reload``  (from the ``backend/`` directory)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import models  # noqa: F401  — registers every model on Base.metadata
from app.config import get_settings
from app.core.cache import AppCache
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import get_engine, get_sessionmaker, init_engine
from app.routers import (
    ai,
    applications,
    candidate_auth,
    categories,
    health,
    jobs,
    reviews,
    staff_auth,
    subscriptions,
    websocket,
)
from app.services import category_service, job_service, review_service, telegram

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")


async def _init_database() -> None:
    """Prepare the schema (SQLite only), seed defaults, and warm the read cache.

    In production (PostgreSQL) the schema is owned by Alembic — ``alembic upgrade
    head`` runs before the server starts — so we never ``create_all`` there. For
    SQLite (local dev / tests) we create tables on the fly for zero-setup runs.
    """
    init_engine()
    settings = get_settings()
    if settings.is_sqlite:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with get_sessionmaker()() as session:
        await category_service.seed_defaults(session)
        await session.commit()
        await job_service.warm_cache(session)
        await category_service.warm_cache(session)
        await review_service.warm_cache(session)
    AppCache.db_ready = True
    log.info("Database ready; cache warmed (%d jobs, %d categories, %d reviews).",
             len(AppCache.jobs), len(AppCache.categories), len(AppCache.reviews))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up: initializing database and cache.")
    try:
        await _init_database()
    except Exception as exc:  # noqa: BLE001
        AppCache.db_ready = False
        log.error("Database initialization failed: %s", exc)

    await telegram.start()  # no-op without BOT_TOKEN
    yield
    log.info("Shutting down.")
    await telegram.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Recruitment platform API (modular monolith). Public read endpoints are "
            "cache-served with ETag/Cache-Control; staff routes use JWT + role gating."
        ),
        lifespan=lifespan,
    )

    # Rate limiting (slowapi) — brute-force protection on auth/AI/subscribe routes.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # CORS: restricted to the known frontend origins. Credentials off — auth uses
    # the Authorization (Bearer) header, not cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Request-ID", "ETag"],
    )

    # Correlation id + access logging, and conservative security headers.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    for module in (
        health, staff_auth, candidate_auth, jobs, categories, reviews,
        applications, subscriptions, ai, websocket,
    ):
        app.include_router(module.router)

    return app


app = create_app()
