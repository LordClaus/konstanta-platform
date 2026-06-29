# ─────────────────────────────────────────────────────────────────────────────
# Konstanta — single image. uvicorn serves the API and runs the Telegram bot
# in-process (webhook when PUBLIC_URL is set, else long-polling). The container
# applies Alembic migrations on start, then serves.
#   backend (app package) → /app/backend   ;   bot package → /app/telegram_bot
# ─────────────────────────────────────────────────────────────────────────────
# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# ── Dependencies first (cached layer; rebuilt only when requirements change) ──
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY backend/ /app/backend/
COPY telegram_bot/ /app/telegram_bot/
COPY docker/entrypoint.sh /app/entrypoint.sh

# ── Drop root privileges ──────────────────────────────────────────────────────
RUN chmod +x /app/entrypoint.sh \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser /app
USER appuser

# Run from the backend dir so `app` (and alembic.ini) resolve; the entrypoint
# adds the repo root for `import telegram_bot`.
WORKDIR /app/backend
EXPOSE 8000

CMD ["/app/entrypoint.sh"]
