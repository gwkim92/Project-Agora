#!/usr/bin/env bash
set -euo pipefail

# Deploy Agora core contracts with Foundry.
#
# Usage (Base Sepolia example):
#   export RPC_URL="https://base-sepolia.g.alchemy.com/v2/..."
#   export DEPLOYER_PRIVATE_KEY="0x..."
#   export AGORA_OWNER="0x<safe_or_owner>"
#   export AGORA_SLASHER="0x<safe_or_ops>"
#   export AGORA_USDC="0x<usdc_on_target_chain>"
#   export ETHERSCAN_API_KEY="..."   # optional, for --verify
#
#   ./scripts/deploy_contracts.sh --network base-sepolia --verify
#
# Notes:
# - This script only deploys. You still need to set server env vars to the printed addresses.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACTS_DIR="${ROOT_DIR}/contracts"

NETWORK="base-sepolia"
VERIFY="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --network)
      NETWORK="${2:-}"
      shift 2
      ;;
    --verify)
      VERIFY="1"
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${RPC_URL:-}" ]]; then
  echo "RPC_URL is required" >&2
  exit 1
fi
if [[ -z "${DEPLOYER_PRIVATE_KEY:-}" ]]; then
  echo "DEPLOYER_PRIVATE_KEY is required" >&2
  exit 1
fi
if [[ -z "${AGORA_OWNER:-}" || -z "${AGORA_SLASHER:-}" || -z "${AGORA_USDC:-}" ]]; then
  echo "AGORA_OWNER / AGORA_SLASHER / AGORA_USDC are required" >&2
  exit 1
fi

cd "${CONTRACTS_DIR}"

ARGS=(script/DeployAgora.s.sol:DeployAgora --rpc-url "${RPC_URL}" --broadcast)
if [[ "${VERIFY}" == "1" ]]; then
  ARGS+=(--verify)
fi

echo "Deploying contracts to ${NETWORK}…"
forge script "${ARGS[@]}"

