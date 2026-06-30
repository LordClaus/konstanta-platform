# Konstanta — Recruitment Platform

[![CI](https://github.com/LordClaus/konstanta-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/LordClaus/konstanta-platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![Tests](https://img.shields.io/badge/tests-39%20passing-brightgreen)

A production-style recruitment platform built as a **modular monolith**:
a **FastAPI** backend (async **SQLAlchemy 2.0** + **Alembic**), an in-process
**Telegram bot** for managers, a pluggable **AI assistant** (OpenAI / Gemini),
real-time **WebSocket** updates for the CRM, and a static multilingual frontend
for candidates.

> Платформа для кадрової агенції: офіційне працевлаштування за кордоном.
> Кандидати подають анкети на сайті або через Telegram-бота; менеджери опрацьовують
> їх у CRM-панелі в реальному часі. Бекенд — FastAPI + async SQLAlchemy + PostgreSQL.

---

## Tech stack

| Area | Technology |
|------|-----------|
| Language | Python 3.12 |
| Web framework | FastAPI (async), Uvicorn |
| ORM / migrations | SQLAlchemy 2.0 (async, `asyncpg`) · Alembic |
| Database | PostgreSQL (prod) · SQLite/`aiosqlite` (tests) |
| Auth | JWT (PyJWT) · bcrypt · Google OAuth · role-based access |
| AI | OpenAI **or** Gemini behind one provider interface |
| Realtime | WebSockets (CRM panels) |
| Bot | aiogram 3 (in-process; webhook or long-polling) |
| Email / storage | Brevo API · Cloudflare R2 (S3-compatible) |
| Testing | PyTest (unit + e2e) · httpx |
| Tooling | Ruff · Docker · docker-compose · GitHub Actions CI |

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the layering, request lifecycle, and
design rationale, and **[AI_ASSISTANT.md](AI_ASSISTANT.md)** for the prompt design
and OpenAI integration (params, retries, error handling).

---

## Quickstart

### With Docker (PostgreSQL + API + migrations)

```bash
cp .env.example .env          # then set JWT_SECRET (>= 32 bytes)
docker compose up --build
# API on http://localhost:8000  ·  the container runs `alembic upgrade head` first
```

### Local (no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Zero-setup run on SQLite (the app create_all's the schema for SQLite):
DATABASE_URL="sqlite+aiosqlite:///./dev.db" JWT_SECRET="dev-secret-min-32-bytes-aaaaaaaaaaaa" \
  uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### Database migrations (PostgreSQL)

```bash
cd backend
alembic upgrade head            # apply
alembic revision --autogenerate -m "describe change"   # create a new migration
alembic check                   # CI gate: fails if models and migrations drift
```

---

## Tests

```bash
cd backend
pytest          # 39 unit + e2e tests, runs on SQLite (no DB server needed)
pytest --cov=app --cov-report=term-missing   # coverage (CI gate: --cov-fail-under=60)
ruff check .    # lint
mypy            # static type check (CI gate)
```

CI (`.github/workflows/ci.yml`) runs ruff + mypy + pytest (with a coverage gate) on
every push, **and** applies the Alembic migrations against a real PostgreSQL service
to prove they're clean. Dependency bumps are automated via Dependabot.

---

## Project layout

```
konstanta-platform/
├── backend/
│   ├── app/
│   │   ├── main.py             # create_app() factory + lifespan
│   │   ├── config.py           # pydantic-settings (one validated Settings)
│   │   ├── db/                 # async engine, session, declarative Base
│   │   ├── models/             # SQLAlchemy 2.0 ORM (7 tables)
│   │   ├── schemas/            # Pydantic DTOs
│   │   ├── core/               # security, deps, cache, rate-limit, constants
│   │   ├── services/           # business logic (incl. ai/ Strategy+Factory)
│   │   ├── routers/            # thin HTTP/WS endpoints
│   │   └── ws/                 # WebSocket connection manager
│   ├── alembic/                # migration environment + versions
│   ├── tests/                  # unit/ + e2e/
│   ├── requirements.txt        # runtime deps
│   ├── requirements-dev.txt    # + pytest / httpx / ruff
│   └── pyproject.toml          # pytest + ruff config
├── telegram_bot/               # aiogram handlers (run in-process by the API)
├── site/                       # static multilingual candidate frontend + CRM panel
├── docker/entrypoint.sh        # migrate, then serve
├── Dockerfile · docker-compose.yml · .env.example
└── ARCHITECTURE.md
```

---

## Key features

- **Modular monolith** with a strict inward dependency rule (routers → services → models).
- **Async everywhere** — DB, HTTP, bot — so slow I/O never blocks the event loop.
- **In-memory read cache** for hot public endpoints (jobs/categories/reviews),
  warmed at startup and mutated in place on writes — layered with HTTP
  `ETag` / `Cache-Control` so browsers and CDNs revalidate with cheap `304`s.
- **Atomic ticket claim/complete** — invariants encoded in single `UPDATE … WHERE`
  statements; safe across the browser panel and the Telegram button concurrently.
- **Pluggable AI** — swap OpenAI ↔ Gemini via config; provider behind one interface.
- **Event-driven notifications** — candidate status updates and job-alert fan-out
  run fire-and-forget (Email + Telegram) off the request path.
- **Role-based auth** — staff (admin/worker) and candidate realms over one JWT mechanism.
- **Operational hardening** — correlation `X-Request-ID` + access logging on every
  request, security response headers, paginated admin dumps, and `mypy` type-checking in CI.

---

## Configuration

All configuration is environment-driven (12-factor); see **[.env.example](.env.example)**.
Every external integration (AI, email, Telegram, object storage) is **optional** —
the API boots and the test suite passes with none of them set.
