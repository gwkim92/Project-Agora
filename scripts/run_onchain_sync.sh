#!/usr/bin/env bash
set -euo pipefail

# Standalone onchain sync worker (recommended for production).
# Requires:
# - DATABASE_URL (to persist cursors/events)
# - AGORA_ONCHAIN_SYNC_ENABLED=1
# - AGORA_RPC_URL + contract addresses

python3 "server/onchain_worker.py"

