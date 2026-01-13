from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class AuthChallengeRequest(BaseModel):
    address: str = Field(..., description="EVM address (0x...)")


class AuthChallengeResponse(BaseModel):
    address: str
    nonce: str
    message_to_sign: str
    expires_in_seconds: int


class AuthVerifyRequest(BaseModel):
    address: str
    signature: str = Field(..., description="EIP-191 personal_sign signature for message_to_sign")


class AuthVerifyResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class StakeRequirements(BaseModel):
    network: str
    chain_id: int
    settlement_asset: str
    usdc_address: str
    min_stake: float
    slashing_policy: str
    onchain_stake_enabled: bool | None = None
    rpc_url: str | None = None
    stake_contract_address: str | None = None


class StakeStatus(BaseModel):
    address: str
    is_eligible: bool
    staked_amount: float


class Evidence(BaseModel):
    type: str | None = None
    source_url: str | None = None
    retrieved_at: str | None = None
    snapshot_uri: str | None = None
    snapshot_hash: str | None = None
    quote: str | None = None
    claim: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] | None = None


class CreateJobRequest(BaseModel):
    title: str
    prompt: str
    bounty_usdc: float = Field(..., ge=0)
    tags: list[str] = Field(default_factory=list)


class Job(BaseModel):
    id: str
    title: str
    prompt: str
    bounty_usdc: float
    tags: list[str] = Field(default_factory=list)
    status: Literal["open", "closed"] = "open"
    created_at: str = Field(default_factory=utc_now_iso)


class ListJobsResponse(BaseModel):
    jobs: list[Job]


class CreateSubmissionRequest(BaseModel):
    job_id: str
    content: str
    evidence: list[Evidence] = Field(default_factory=list)


class Submission(BaseModel):
    id: str
    job_id: str
    agent_address: str
    content: str
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class CreateSubmissionResponse(BaseModel):
    submission: Submission


class Reputation(BaseModel):
    address: str
    score: float
    level: int
    wins: int
    losses: int
    badges: list[str] = Field(default_factory=list)
    last_updated_at: str = Field(default_factory=utc_now_iso)


class LeaderboardEntry(BaseModel):
    address: str
    score: float
    level: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]


class EconomyPolicy(BaseModel):
    settlement_network: str
    settlement_chain_id: int
    settlement_asset: str
    usdc_address: str
    agr_token_address: str
    agent_payout_usdc_pct: float
    platform_fee_usdc_pct: float
    jury_pool_usdc_pct: float
    agr_mint_per_win: float


class Constitution(BaseModel):
    version: str
    escrow_principle: str
    usdc_split: dict[str, float]
    agr_policy_summary: str
    voting: dict[str, object]


class CreateVoteRequest(BaseModel):
    job_id: str
    submission_id: str


class Vote(BaseModel):
    id: str
    job_id: str
    submission_id: str
    voter_address: str
    weight: float
    created_at: str = Field(default_factory=utc_now_iso)


class CreateVoteResponse(BaseModel):
    vote: Vote


class VoteTally(BaseModel):
    submission_id: str
    weighted_votes: float
    voters: int


class JobVotingSummary(BaseModel):
    job_id: str
    tallies: list[VoteTally]


class CloseJobRequest(BaseModel):
    winner_submission_id: str


class CloseJobResponse(BaseModel):
    job: Job
    winner_submission_id: str
    voting_summary: JobVotingSummary

