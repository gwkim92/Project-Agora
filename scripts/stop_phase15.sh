#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/scripts/runtime"

say() { echo "[phase1.5] $*"; }

kill_pid_file() {
  local name="$1"
  local f="${RUNTIME_DIR}/${name}.pid"
  if [[ -f "${f}" ]]; then
    local pid
    pid="$(cat "${f}" || true)"
    if [[ -n "${pid}" ]]; then
      kill -TERM "${pid}" >/dev/null 2>&1 || true
      say "stopped ${name} (pid ${pid})"
    fi
    rm -f "${f}"
  fi
}

kill_pid_file api
kill_pid_file web

say "done"

