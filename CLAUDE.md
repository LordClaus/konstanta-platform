# CLAUDE.md

Orientation for AI assistants (and humans) working in this repo.

## What this is
Konstanta — a recruitment platform built as a **modular monolith**: an async
FastAPI backend (SQLAlchemy 2.0 + Alembic, PostgreSQL/SQLite), an in-process
aiogram Telegram bot, a pluggable AI assistant (OpenAI/Gemini), WebSocket CRM
updates, and a static multilingual frontend. Full design in **ARCHITECTURE.md**.

## Layering (dependencies point inward — never outward)
```
routers/  → HTTP/WS transport (parse, authorize, delegate)
services/ → business logic (no FastAPI/HTTP types here)
models/   → SQLAlchemy ORM
core/ db/ → config, security, deps, cache, rate-limit, sessions
```
When adding a feature: add a `schemas/` DTO, put logic in a `services/` function,
expose it from a thin `routers/` endpoint. Keep ORM→wire mapping in
`services/serializers.py`.

## Dev commands (run from `backend/`)
```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements-dev.txt

pytest                 # unit + e2e (SQLite, no DB server needed)
ruff check .           # lint (CI gate)
alembic upgrade head   # apply migrations (PostgreSQL)
alembic check          # fail if models and migrations drift
uvicorn app.main:app --reload   # local dev (set DATABASE_URL + JWT_SECRET)
```
Full stack: `docker compose up --build` from the repo root.

## Conventions
- Python 3.12, async end-to-end. Type-annotated ORM (`Mapped`/`mapped_column`).
- One validated `Settings` (pydantic-settings) in `app/config.py`; all config via env.
- Every external integration (AI, email, Telegram, R2) is optional and degrades safely.
- Tests must stay green and ruff clean before commit; keep migrations in sync.
