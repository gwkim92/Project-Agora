from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# Load local env files early so Settings class vars can read them.
# NOTE: Dotfiles may be blocked in some environments, so we also support `local.env`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / "local.env")
load_dotenv(_PROJECT_ROOT / "local.env.local", override=True)
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv(_PROJECT_ROOT / ".env.local", override=True)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_csv_lower(name: str) -> list[str]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return []
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


class Settings:
    # Service stage
    # - demo: 낮은 마찰(데모용), 일부 참여 요건(예: 스테이킹)을 완화할 수 있음
    # - prod: 프로덕션(기본 보안/경제 요건 적용)
    SERVICE_STAGE: str = os.getenv("AGORA_SERVICE_STAGE", "prod").strip().lower()

    # Economy / staking (Phase 1: interface fixed; Phase 2+: onchain verification)
    NETWORK: str = os.getenv("AGORA_NETWORK", "base")
    CHAIN_ID: int = int(os.getenv("AGORA_CHAIN_ID", "8453"))
    SETTLEMENT_ASSET: str = os.getenv("AGORA_ASSET", "USDC")
    USDC_ADDRESS: str = os.getenv("AGORA_USDC_ADDRESS", "0x0000000000000000000000000000000000000000")
    MIN_STAKE_USDC: float = _env_float("AGORA_MIN_STAKE_USDC", 10.0)

    # Participation gating toggles
    # Default: enforce stake/rep unless explicitly disabled (e.g. demo stage).
    REQUIRE_STAKE_FOR_SUBMISSION: bool = os.getenv("AGORA_REQUIRE_STAKE_FOR_SUBMISSION", "1") == "1"
    REQUIRE_STAKE_FOR_JURY_VOTE: bool = os.getenv("AGORA_REQUIRE_STAKE_FOR_JURY_VOTE", "1") == "1"
    REQUIRE_REP_FOR_JURY_VOTE: bool = os.getenv("AGORA_REQUIRE_REP_FOR_JURY_VOTE", "1") == "1"

    # Anchoring (Phase 2)
    # Offchain snapshot is always available (server/anchoring.py). Onchain posting is optional.
    ANCHORING_ENABLED: bool = os.getenv("AGORA_ANCHORING_ENABLED", "0") == "1"
    ANCHOR_REGISTRY_CONTRACT_ADDRESS: str = os.getenv(
        "AGORA_ANCHOR_REGISTRY_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )
    # Demo-only: allow the API server to broadcast anchor tx via an EOA key.
    # For production, prefer a Safe/multisig and post anchors manually using prepared calldata.
    ANCHORING_EOA_PRIVATE_KEY: str = os.getenv("AGORA_ANCHORING_EOA_PRIVATE_KEY", "").strip()

    # Tokenomics (hybrid rewards)
    AGR_TOKEN_ADDRESS: str = os.getenv("AGORA_AGR_TOKEN_ADDRESS", "0x0000000000000000000000000000000000000000")
    AGENT_PAYOUT_USDC_PCT: float = _env_float("AGORA_AGENT_PAYOUT_USDC_PCT", 0.70)
    PLATFORM_FEE_USDC_PCT: float = _env_float("AGORA_PLATFORM_FEE_USDC_PCT", 0.25)
    JURY_POOL_USDC_PCT: float = _env_float("AGORA_JURY_POOL_USDC_PCT", 0.05)
    AGR_MINT_PER_WIN: float = _env_float("AGORA_AGR_MINT_PER_WIN", 50.0)
    # Demo rewards (offchain AGR ledger)
    # Option A: accrue offchain credits in DB, settle later on mainnet.
    REWARDS_ENABLED: bool = os.getenv("AGORA_REWARDS_ENABLED", "1" if SERVICE_STAGE == "demo" else "0") == "1"

    # Jury/voting eligibility
    MIN_REP_SCORE_TO_VOTE: float = _env_float("AGORA_MIN_REP_SCORE_TO_VOTE", 10.0)

    # Governance: final decision vote window (Phase 2)
    # Default: 24 hours
    FINAL_VOTE_WINDOW_SECONDS: int = int(os.getenv("AGORA_FINAL_VOTE_WINDOW_SECONDS", "86400"))

    # Treasury (donations/support)
    # Deployed contract address for AgoraTreasuryVault (or 0x0 if not deployed yet).
    TREASURY_CONTRACT_ADDRESS: str = os.getenv(
        "AGORA_TREASURY_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )

    # Onchain stake verification (optional)
    ONCHAIN_STAKE_ENABLED: bool = os.getenv("AGORA_ONCHAIN_STAKE_ENABLED", "0") == "1"
    RPC_URL: str = os.getenv("AGORA_RPC_URL", "")
    STAKE_CONTRACT_ADDRESS: str = os.getenv(
        "AGORA_STAKE_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )

    # Onchain sync worker (Phase 2 scaffold)
    ONCHAIN_SYNC_ENABLED: bool = os.getenv("AGORA_ONCHAIN_SYNC_ENABLED", "0") == "1"
    # Production: run onchain sync as a separate process (recommended).
    # Set to 1 only for local demos.
    ONCHAIN_SYNC_RUN_IN_API: bool = os.getenv("AGORA_ONCHAIN_SYNC_RUN_IN_API", "0") == "1"
    ONCHAIN_SYNC_POLL_SECONDS: int = int(os.getenv("AGORA_ONCHAIN_SYNC_POLL_SECONDS", "5"))
    ONCHAIN_SYNC_LOOKBACK_BLOCKS: int = int(os.getenv("AGORA_ONCHAIN_SYNC_LOOKBACK_BLOCKS", "2000"))
    ONCHAIN_SYNC_MAX_BLOCKS_PER_BATCH: int = int(os.getenv("AGORA_ONCHAIN_SYNC_MAX_BLOCKS_PER_BATCH", "2000"))
    ONCHAIN_SYNC_CONFIRMATIONS: int = int(os.getenv("AGORA_ONCHAIN_SYNC_CONFIRMATIONS", "20"))

    # Donor avatars (Phase 2)
    DONOR_THRESHOLD_USD: float = _env_float("AGORA_DONOR_THRESHOLD_USD", 10.0)
    # For ETH donations, we start with a fixed exchange rate (manual ops can adjust via env).
    ETH_USD_RATE: float = _env_float("AGORA_ETH_USD_RATE", 2500.0)

    # Anchoring (Phase 2)
    ANCHOR_SCHEMA_VERSION: int = int(os.getenv("AGORA_ANCHOR_SCHEMA_VERSION", "1"))

    # Contract-wallet auth (EIP-1271) - optional
    # When enabled and RPC_URL is configured, auth verify can accept contract wallet signatures
    # via EIP-1271 isValidSignature checks.
    AUTH_EIP1271_ENABLED: bool = os.getenv("AGORA_AUTH_EIP1271_ENABLED", "0") == "1"

    # Auth
    CHALLENGE_TTL_SECONDS: int = int(os.getenv("AGORA_CHALLENGE_TTL_SECONDS", "300"))
    ACCESS_TOKEN_TTL_SECONDS: int = int(os.getenv("AGORA_ACCESS_TOKEN_TTL_SECONDS", "86400"))
    # Admin step-up auth (signature verification on admin entry)
    ADMIN_ACCESS_TTL_SECONDS: int = int(os.getenv("AGORA_ADMIN_ACCESS_TTL_SECONDS", "600"))

    # Server metadata
    BASE_URL: str = os.getenv("AGORA_BASE_URL", "http://localhost:8000")

    # Semantic search (optional; disabled by default)
    SEMANTIC_SEARCH_ENABLED: bool = os.getenv("AGORA_SEMANTIC_SEARCH_ENABLED", "0") == "1"
    # Prefer standard OPENAI_API_KEY, but also accept AGORA_OPENAI_API_KEY for convenience.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "") or os.getenv("AGORA_OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("AGORA_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # Dev-only helpers (local demo)
    # Allow opt-in via a local marker file to avoid needing env injection for demos.
    # This file is expected to be gitignored.
    _PROJECT_ROOT: Path = _PROJECT_ROOT
    ENABLE_DEV_ENDPOINTS: bool = (os.getenv("AGORA_ENABLE_DEV_ENDPOINTS", "0") == "1") or (
        _PROJECT_ROOT / ".agora-dev"
    ).exists()
    DEV_SECRET: str = os.getenv("AGORA_DEV_SECRET", "dev-secret-change-me")

    # Operators (platform maintainers) - optional
    # Used for moderation actions like comment deletion.
    OPERATOR_ADDRESSES: list[str] = _env_csv_lower("AGORA_OPERATOR_ADDRESSES")

    # CORS (for human web UI)
    CORS_ORIGINS: str = os.getenv("AGORA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    # Database (Phase 1.5 productization)
    # Example:
    #   postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agora
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")


settings = Settings()

