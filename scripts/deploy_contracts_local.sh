#!/usr/bin/env bash
set -euo pipefail

# Cheapest local contract set:
# - start anvil
# - deploy MockUSDC + Agora contracts
# - write contracts/deployments/local.json
#
# Requirements:
# - foundry (anvil/forge)
#
# Usage:
#   ./scripts/deploy_contracts_local.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACTS_DIR="${ROOT_DIR}/contracts"

RPC_URL="${RPC_URL:-http://localhost:8545}"
ANVIL_PORT="${ANVIL_PORT:-8545}"

if ! command -v anvil >/dev/null 2>&1; then
  echo "anvil not found. Install foundry first." >&2
  exit 1
fi
if ! command -v forge >/dev/null 2>&1; then
  echo "forge not found. Install foundry first." >&2
  exit 1
fi

if ! lsof -nP -iTCP:"${ANVIL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Starting anvil on ${RPC_URL}…"
  nohup anvil --port "${ANVIL_PORT}" >/tmp/agora-anvil.log 2>&1 &
  sleep 0.5
fi

# Use anvil default account #0 private key unless overridden.
DEPLOYER_PRIVATE_KEY="${DEPLOYER_PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"

cd "${CONTRACTS_DIR}"

echo "Deploying local contract set (anvil)…"
AGORA_DEPLOYMENT_SET="local" \
AGORA_DEPLOY_MOCK_USDC=1 \
DEPLOYER_PRIVATE_KEY="${DEPLOYER_PRIVATE_KEY}" \
forge script script/DeployAgora.s.sol:DeployAgora --rpc-url "${RPC_URL}" --broadcast

echo "Wrote: ${CONTRACTS_DIR}/deployments/local.json"

