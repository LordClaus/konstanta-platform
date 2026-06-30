"""The atomic ticket claim/complete invariants in application_service — the core
concurrency guard behind the CRM 'Take to Work' button and the Telegram button.

Runs against an isolated in-memory SQLite engine (StaticPool, single connection)
so the single-UPDATE WHERE-clause guards are exercised directly, without HTTP/WS
or the app's shared engine, and with no write-lock races.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  — register models on Base.metadata
from app.db.base import Base
from app.models import Application
from app.services import application_service as svc


@pytest.fixture
async def sm(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    # perform_lock/complete open their own session via this factory.
    monkeypatch.setattr(svc, "get_sessionmaker", lambda: maker)
    yield maker
    await engine.dispose()


async def _new_ticket(maker) -> int:
    async with maker() as s:
        app = Application(name="N", phone="+420", status="new")
        s.add(app)
        await s.flush()
        app_id = app.id
        await s.commit()
        return app_id


async def _row(maker, app_id):
    async with maker() as s:
        return (await s.execute(
            select(Application.status, Application.manager_name).where(Application.id == app_id)
        )).first()


async def test_lock_then_complete_happy_path(sm):
    app_id = await _new_ticket(sm)
    assert await svc.perform_lock(app_id, "alice") == (True, None)
    assert await _row(sm, app_id) == ("processing", "alice")
    assert await svc.perform_complete(app_id, "alice") == (True, None)
    assert (await _row(sm, app_id))[0] == "completed"


async def test_one_active_ticket_per_manager(sm):
    a1 = await _new_ticket(sm)
    a2 = await _new_ticket(sm)
    assert await svc.perform_lock(a1, "alice") == (True, None)

    ok, msg = await svc.perform_lock(a2, "alice")  # alice already busy
    assert ok is False
    assert "актив" in msg.lower()
    assert (await _row(sm, a2))[0] == "new"  # second ticket untouched


async def test_cannot_double_claim_a_processing_ticket(sm):
    app_id = await _new_ticket(sm)
    assert await svc.perform_lock(app_id, "alice") == (True, None)

    ok, _msg = await svc.perform_lock(app_id, "bob")  # already taken by alice
    assert ok is False
    assert await _row(sm, app_id) == ("processing", "alice")  # still alice's


async def test_complete_only_by_the_claiming_manager(sm):
    app_id = await _new_ticket(sm)
    await svc.perform_lock(app_id, "alice")

    ok, _msg = await svc.perform_complete(app_id, "bob")  # not the owner
    assert ok is False
    assert (await _row(sm, app_id))[0] == "processing"

    assert await svc.perform_complete(app_id, "alice") == (True, None)


async def test_complete_requires_a_manager_name(sm):
    app_id = await _new_ticket(sm)
    await svc.perform_lock(app_id, "alice")
    assert await svc.perform_complete(app_id, "") == (False, "Authentication required.")
