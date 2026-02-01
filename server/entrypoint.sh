#!/usr/bin/env sh
set -eu

# Production-ish container entrypoint:
# - If DATABASE_URL is configured, run Alembic migrations before starting the API.
# - Then exec the provided command (uvicorn by default).

if [ -n "${DATABASE_URL:-}" ]; then
  echo "[entrypoint] DATABASE_URL set; running alembic upgrade head"
  alembic -c /app/server/alembic.ini upgrade head
else
  echo "[entrypoint] DATABASE_URL empty; skipping alembic migrations"
fi

exec "$@"

