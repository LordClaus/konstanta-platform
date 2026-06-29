# Architecture

Konstanta is a **modular monolith**: one deployable FastAPI service, internally
split into clear layers and feature modules. This document describes the layering,
the request lifecycle, and the design decisions behind them.

> TL;DR — routers do HTTP, services do logic, models do persistence, `core`/`db`
> do cross-cutting infrastructure. Dependencies always point *inward*.

---

## 1. Layering

```
            ┌──────────────────────────────────────────────────────┐
 HTTP / WS  │                     app/routers/                     │  transport only:
            │   health · staff_auth · candidate_auth · jobs ·      │  parse, authorize,
            │   categories · reviews · applications · subscriptions│  delegate, serialize
            │   · ai · websocket                                   │
            └───────────────────────────┬──────────────────────────┘
                                         │ calls
            ┌───────────────────────────▼──────────────────────────┐
 Business   │                     app/services/                    │  all domain logic;
            │   job · category · review · application · auth ·     │  no FastAPI types,
            │   subscription · notification · storage · ai/* ·     │  no HTTP awareness
            │   telegram · telegram_gateway · serializers          │
            └───────────────────────────┬──────────────────────────┘
                                         │ uses
            ┌───────────────────────────▼──────────────────────────┐
 Persistence│        app/models/ (SQLAlchemy 2.0 ORM)              │  one class per table
            └───────────────────────────┬──────────────────────────┘
                                         │ on
            ┌───────────────────────────▼──────────────────────────┐
 Infra      │  app/db/ (engine, session, Base)  ·  app/core/       │  cross-cutting:
            │  (config, security, deps, cache, rate_limit,         │  auth, settings,
            │  constants)  ·  app/ws/ (ConnectionManager)          │  caching, sessions
            └──────────────────────────────────────────────────────┘
```

**The dependency rule:** an outer layer may import an inner one, never the reverse.
A router imports a service; a service imports models/core; nothing in `services`
imports from `routers`. This keeps the business logic unit-testable without HTTP.

---

## 2. Module map

| Layer | Module | Responsibility |
|------|--------|----------------|
| config | `app/config.py` | One validated `Settings` (pydantic-settings), env-driven, cached |
| db | `app/db/session.py` | Lazy async engine + `async_sessionmaker` + `get_session` dependency |
| db | `app/db/base.py` | Declarative `Base` |
| models | `app/models/*` | `Application, Job, Category, Review, Staff, User, Subscription` |
| schemas | `app/schemas/*` | Pydantic request/response DTOs (the wire contract) |
| core | `app/core/security.py` | bcrypt hashing, JWT issue/verify, Google OAuth, age gate |
| core | `app/core/deps.py` | `get_current_staff`, `require_role`, `get_current_candidate` |
| core | `app/core/cache.py` | `AppCache` — in-memory read cache for hot public endpoints |
| core | `app/core/rate_limit.py` | slowapi limiter |
| core | `app/core/constants.py` | site keys, default categories, pure helpers (slug, cities…) |
| services | `app/services/*` | business logic per domain (see layering diagram) |
| services | `app/services/ai/*` | provider-agnostic AI (Strategy + Factory) |
| ws | `app/ws/manager.py` | WebSocket fan-out hub for CRM panels |
| app | `app/main.py` | `create_app()` factory + lifespan (init DB, seed, warm cache, bot) |

---

## 3. Request lifecycle (example: `POST /jobs`)

```
client → CORS → slowapi → router(jobs.create_job)
                              │  Depends(require_role("admin"))   ← JWT verified
                              │  Depends(get_session)             ← async DB session
                              ▼
                          job_service.create_job(session, data)
                              │  INSERT via ORM  +  AppCache.insert_job(...)
                              ▼
                          notification_service.fanout_job_alert(entry)   ← fire-and-forget
                              ▼
                          {"status": "success", "id": ...}
```

Reads (`GET /jobs`, `/categories`, `/reviews`) skip the database entirely and are
served from `AppCache`, which is warmed at startup and mutated in place on every
write — the platform's main web-performance optimization.

---

## 4. Key design decisions

### Modular monolith (not microservices)
One process, one image, one deploy — but internally decomposed by feature and by
layer. This is the right size for the domain: low operational overhead, yet every
module has a single responsibility and a testable seam. Splitting into services
later means lifting a `services/` package out behind its existing interface.

### SOLID / DRY / YAGNI in practice
- **S** — each service owns one domain; routers only translate HTTP.
- **O** — AI providers implement `AIProvider`; adding OpenAI/Gemini/Anthropic is a
  new class + one factory line, no changes to the route or service (`ai/base.py`,
  `ai/factory.py`).
- **D** — routers depend on the `AIProvider` abstraction and on service functions,
  not on vendors or SQL. The Telegram bot depends on a `gateway`/`bridge` seam, not
  on the API module, which also breaks a would-be circular import.
- **DRY** — `TimestampMixin` defines `created_at` once; `serializers.py` is the one
  place ORM→wire mapping lives; `constants.py` holds shared pure helpers.
- **YAGNI** — no repository abstraction over SQLAlchemy, no event bus: the cache +
  fire-and-forget tasks cover the actual requirements without ceremony.

### Async end-to-end
FastAPI + SQLAlchemy 2.0 async (`asyncpg`) + aiohttp. A slow DB round-trip or a
slow upstream (AI/email/Telegram) never blocks the event loop that also serves the
WebSocket hub and the in-process bot.

### Atomic state transitions
Ticket claim/complete are single `UPDATE … WHERE` statements whose predicates
encode every invariant (status guard, "one active ticket per manager", ownership),
so two managers — browser panel **and** Telegram button — can never double-claim.
See `services/application_service.py`.

### Background work is fire-and-forget
Candidate notifications and job-alert fan-out run via `asyncio.create_task` with a
strong-ref set (GC guard) and their own DB session, so user-facing requests stay
fast and the bottleneck server stays responsive.

### Schema is owned by Alembic
PostgreSQL in production; the container runs `alembic upgrade head` before serving.
The test suite runs on SQLite (`aiosqlite`) for zero-setup CI — the same ORM models
drive both, and `alembic check` in CI fails the build if models and migrations drift.

---

## 5. Data model

| Table | Notes |
|------|-------|
| `applications` | lifecycle `new → processing → completed`; carries optional Telegram chat id + lang for status pushes |
| `jobs` | `type` is a soft reference to `categories.id`; `sites`/`cities` are JSON (multi-site placement, per-city housing) |
| `categories` | admin-managed; `id` is a slug; trilingual labels |
| `reviews` | public testimonials, tagged by site |
| `staff` | internal CRM users (admin/worker); login-only |
| `users` | public candidates (email/password or Google; 18+) |
| `subscriptions` | job-alert recipients (email and/or Telegram); NULL category/site = "all" |

---

## 6. External integrations

| Integration | Where | Failure mode |
|-------------|-------|--------------|
| AI (OpenAI / Gemini) | `services/ai/*` | unconfigured → `503`; upstream error/timeout → `502/504` |
| Email (Brevo) | `services/notification_service.py` | best-effort; logged, never blocks |
| Telegram bot (aiogram) | `services/telegram*.py` + `telegram_bot/` | optional; absent without `BOT_TOKEN` |
| Object storage (R2/S3) | `services/storage.py` | unconfigured → `503` on image upload only |

All four are optional: the API boots and the test suite runs green with none of
them configured.

The AI assistant (provider abstraction, prompt design, OpenAI integration with
configurable params + bounded retry) is documented separately in
**[AI_ASSISTANT.md](AI_ASSISTANT.md)**.
