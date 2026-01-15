from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class Settings:
    # Economy / staking (Phase 1: interface fixed; Phase 2+: onchain verification)
    NETWORK: str = os.getenv("AGORA_NETWORK", "base")
    CHAIN_ID: int = int(os.getenv("AGORA_CHAIN_ID", "8453"))
    SETTLEMENT_ASSET: str = os.getenv("AGORA_ASSET", "USDC")
    USDC_ADDRESS: str = os.getenv("AGORA_USDC_ADDRESS", "0x0000000000000000000000000000000000000000")
    MIN_STAKE_USDC: float = _env_float("AGORA_MIN_STAKE_USDC", 10.0)

    # Tokenomics (hybrid rewards)
    AGR_TOKEN_ADDRESS: str = os.getenv("AGORA_AGR_TOKEN_ADDRESS", "0x0000000000000000000000000000000000000000")
    AGENT_PAYOUT_USDC_PCT: float = _env_float("AGORA_AGENT_PAYOUT_USDC_PCT", 0.70)
    PLATFORM_FEE_USDC_PCT: float = _env_float("AGORA_PLATFORM_FEE_USDC_PCT", 0.25)
    JURY_POOL_USDC_PCT: float = _env_float("AGORA_JURY_POOL_USDC_PCT", 0.05)
    AGR_MINT_PER_WIN: float = _env_float("AGORA_AGR_MINT_PER_WIN", 50.0)

    # Jury/voting eligibility
    MIN_REP_SCORE_TO_VOTE: float = _env_float("AGORA_MIN_REP_SCORE_TO_VOTE", 10.0)

    # Onchain stake verification (optional)
    ONCHAIN_STAKE_ENABLED: bool = os.getenv("AGORA_ONCHAIN_STAKE_ENABLED", "0") == "1"
    RPC_URL: str = os.getenv("AGORA_RPC_URL", "")
    STAKE_CONTRACT_ADDRESS: str = os.getenv(
        "AGORA_STAKE_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000"
    )

    # Auth
    CHALLENGE_TTL_SECONDS: int = int(os.getenv("AGORA_CHALLENGE_TTL_SECONDS", "300"))
    ACCESS_TOKEN_TTL_SECONDS: int = int(os.getenv("AGORA_ACCESS_TOKEN_TTL_SECONDS", "86400"))

    # Server metadata
    BASE_URL: str = os.getenv("AGORA_BASE_URL", "http://localhost:8000")

    # Dev-only helpers (local demo)
    ENABLE_DEV_ENDPOINTS: bool = os.getenv("AGORA_ENABLE_DEV_ENDPOINTS", "0") == "1"
    DEV_SECRET: str = os.getenv("AGORA_DEV_SECRET", "dev-secret-change-me")

    # CORS (for human web UI)
    CORS_ORIGINS: str = os.getenv("AGORA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")


settings = Settings()

