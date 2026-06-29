#!/bin/sh
# Container entrypoint: apply DB migrations, then serve the API (+ in-process bot).
set -e

cd /app/backend

echo "Applying database migrations (alembic upgrade head)…"
alembic upgrade head

echo "Starting API on port ${PORT:-8000}…"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
