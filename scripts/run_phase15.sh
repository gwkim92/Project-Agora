#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/scripts/runtime"
mkdir -p "${RUNTIME_DIR}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-3000}"

PG_CONTAINER="${PG_CONTAINER:-agora-postgres-phase15}"
PG_PORT="${PG_PORT:-6543}"
PG_IMAGE="${PG_IMAGE:-postgres:15-alpine}"
PG_USER="${PG_USER:-agora}"
PG_PASS="${PG_PASS:-agora}"
PG_DB="${PG_DB:-agora}"
PG_VOLUME="${PG_VOLUME:-agora_pgdata_phase15}"

# Optional Redis for rate limiting (only started if WITH_REDIS=1)
WITH_REDIS="${WITH_REDIS:-0}"
REDIS_CONTAINER="${REDIS_CONTAINER:-agora-redis-phase15}"
REDIS_PORT="${REDIS_PORT:-6385}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:7-alpine}"

SMOKE="${SMOKE:-1}"

say() { echo "[phase1.5] $*"; }

is_listening() {
  local port="$1"
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    say "docker not found; install Docker Desktop first."
    exit 1
  fi
  if docker ps >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    say "Docker daemon not reachable. Trying to start Docker Desktop…"
    open -a Docker >/dev/null 2>&1 || true
    for _ in $(seq 1 60); do
      docker ps >/dev/null 2>&1 && return 0
      sleep 0.5
    done
  fi
  say "Docker daemon still not reachable. Start Docker Desktop and retry."
  exit 1
}

ensure_python_venv() {
  if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    say "missing .venv. Create it first: python3 -m venv .venv"
    exit 1
  fi
}

pip_install_server_deps() {
  say "Ensuring server deps are installed in .venv…"
  "${ROOT_DIR}/.venv/bin/pip" install -q -r "${ROOT_DIR}/server/requirements.txt"
}

start_postgres() {
  ensure_docker
  if is_listening "${PG_PORT}"; then
    say "Postgres port ${PG_PORT} already in use; skipping container start."
    return 0
  fi

if docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
    say "Postgres container already running: ${PG_CONTAINER}"
  else
    if docker ps -a --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
      say "Starting existing Postgres container: ${PG_CONTAINER}"
      docker start "${PG_CONTAINER}" >/dev/null
    else
      say "Starting Postgres container: ${PG_CONTAINER} on 127.0.0.1:${PG_PORT}"
      docker run -d \
        --name "${PG_CONTAINER}" \
        -e POSTGRES_USER="${PG_USER}" \
        -e POSTGRES_PASSWORD="${PG_PASS}" \
        -e POSTGRES_DB="${PG_DB}" \
        -p "127.0.0.1:${PG_PORT}:5432" \
        -v "${PG_VOLUME}:/var/lib/postgresql/data" \
        "${PG_IMAGE}" >/dev/null
    fi
  fi

  say "Waiting for Postgres readiness…"
  for _ in $(seq 1 60); do
    docker exec "${PG_CONTAINER}" pg_isready -U "${PG_USER}" -d "${PG_DB}" >/dev/null 2>&1 && break
    sleep 0.5
  done
  docker exec "${PG_CONTAINER}" pg_isready -U "${PG_USER}" -d "${PG_DB}" >/dev/null
  say "Postgres ready."
}

start_redis_optional() {
  if [[ "${WITH_REDIS}" != "1" ]]; then
    return 0
  fi
  ensure_docker
  if is_listening "${REDIS_PORT}"; then
    say "Redis port ${REDIS_PORT} already in use; skipping container start."
    return 0
  fi
  if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
    say "Redis container already running: ${REDIS_CONTAINER}"
    return 0
  fi
  if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
    say "Starting existing Redis container: ${REDIS_CONTAINER}"
    docker start "${REDIS_CONTAINER}" >/dev/null
  else
    say "Starting Redis container: ${REDIS_CONTAINER} on 127.0.0.1:${REDIS_PORT}"
    docker run -d \
      --name "${REDIS_CONTAINER}" \
      -p "127.0.0.1:${REDIS_PORT}:6379" \
      "${REDIS_IMAGE}" >/dev/null
  fi
  say "Redis started."
}

run_migrations() {
  say "Running alembic migrations…"
  (cd "${ROOT_DIR}/server" && "${ROOT_DIR}/.venv/bin/alembic" upgrade head)
  say "Migrations applied."
}

start_api() {
  if is_listening "${API_PORT}"; then
    say "API already listening on ${API_HOST}:${API_PORT}; skipping start."
    return 0
  fi

  say "Starting API on ${API_HOST}:${API_PORT}…"
  local env_args=()
  if [[ "${WITH_REDIS}" == "1" ]]; then
    env_args+=( "REDIS_URL=redis://${WEB_HOST}:${REDIS_PORT}/0" )
  fi

  # EIP-1271 support stays off by default; enable by exporting AGORA_AUTH_EIP1271_ENABLED=1 and AGORA_RPC_URL.
  # local.env is read automatically by server/config.py.

  (cd "${ROOT_DIR}" && \
    env "${env_args[@]}" \
    "${ROOT_DIR}/.venv/bin/uvicorn" server.main:app --host "${API_HOST}" --port "${API_PORT}" \
    >"${RUNTIME_DIR}/api.log" 2>&1 & echo $! > "${RUNTIME_DIR}/api.pid")

  for _ in $(seq 1 40); do
    curl -sS "http://${API_HOST}:${API_PORT}/healthz" >/dev/null 2>&1 && break
    sleep 0.25
  done
  curl -sS "http://${API_HOST}:${API_PORT}/healthz" >/dev/null
  say "API up."
}

start_web() {
  if [[ ! -d "${ROOT_DIR}/web" ]]; then
    return 0
  fi
  if is_listening "${WEB_PORT}"; then
    say "Web already listening on ${WEB_HOST}:${WEB_PORT}; skipping start."
    return 0
  fi
  say "Starting Web on ${WEB_HOST}:${WEB_PORT}…"
  (cd "${ROOT_DIR}/web" && \
    npm run -s dev -- --port "${WEB_PORT}" >"${RUNTIME_DIR}/web.log" 2>&1 & echo $! > "${RUNTIME_DIR}/web.pid")
  for _ in $(seq 1 80); do
    curl -sS "http://${WEB_HOST}:${WEB_PORT}/" >/dev/null 2>&1 && break
    sleep 0.25
  done
  say "Web started (may still be compiling)."
}

smoke() {
  say "Smoke checks…"
  curl -sS "http://${API_HOST}:${API_PORT}/healthz" >/dev/null
  curl -sS "http://${API_HOST}:${API_PORT}/readyz" >/dev/null || true
  curl -sS "http://${API_HOST}:${API_PORT}/api/v1/jobs?status=all" >/dev/null

  say "Running SDK E2E (dev endpoints)…"
  "${ROOT_DIR}/.venv/bin/pip" install -q -r "${ROOT_DIR}/sdk/python/requirements.txt"
  AGORA_BASE_URL="http://${API_HOST}:${API_PORT}" \
  AGORA_DEV_SECRET="${AGORA_DEV_SECRET:-<set-a-random-secret>}" \
    "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/sdk/python/examples/agent_end_to_end.py" >/dev/null

  say "Smoke OK."
}

main() {
  ensure_python_venv
  pip_install_server_deps
  start_postgres
  start_redis_optional
  run_migrations
  start_api
  start_web

  if [[ "${SMOKE}" == "1" ]]; then
    smoke
  fi

  cat <<EOF

✅ Phase 1.5 stack is up.

- API: http://${API_HOST}:${API_PORT}
- Web: http://${WEB_HOST}:${WEB_PORT}

Logs:
- ${RUNTIME_DIR}/api.log
- ${RUNTIME_DIR}/web.log

Stop:
- bash scripts/stop_phase15.sh

EOF
}

main "$@"

