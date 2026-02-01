#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "[contracts] docker not found (needed to run foundry in container)"
  exit 1
fi

if ! docker ps >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "[contracts] Docker daemon not reachable. Trying to start Docker Desktop…"
    open -a Docker >/dev/null 2>&1 || true
    for _ in $(seq 1 60); do
      docker ps >/dev/null 2>&1 && break
      sleep 0.5
    done
  fi
fi

echo "[contracts] running forge test…"
docker run --rm \
  -v "${ROOT_DIR}:/repo" \
  -w /repo/contracts \
  --entrypoint sh \
  ghcr.io/foundry-rs/foundry:stable \
  -lc "set -e; if [ ! -d lib/forge-std ]; then echo '[contracts] installing forge-std…'; forge install foundry-rs/forge-std; fi; forge test -vvv"

