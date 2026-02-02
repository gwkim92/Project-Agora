from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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
    # Phase 2+: optional onchain anchors for last stake update (if available).
    stake_tx_hash: str | None = None
    stake_chain_id: int | None = None
    stake_contract_address: str | None = None
    stake_block_number: int | None = None
    stake_log_index: int | None = None


class Evidence(BaseModel):
    type: str | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    retrieved_at: str | None = None
    snapshot_uri: str | None = Field(default=None, max_length=4096)
    snapshot_hash: str | None = Field(default=None, max_length=256)
    quote: str | None = Field(default=None, max_length=4000)
    claim: str | None = Field(default=None, max_length=4000)
    confidence: float | None = None
    metadata: dict[str, Any] | None = None


class CreateJobRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=140)
    prompt: str = Field(..., min_length=1, max_length=20_000)
    bounty_usdc: float = Field(..., ge=0)
    tags: list[str] = Field(default_factory=list, description="Optional tags (max 16)")
    # Final decision vote window override (seconds). If omitted, server default applies.
    final_vote_window_seconds: int | None = Field(default=None, ge=60, le=60 * 60 * 24 * 30)

    @field_validator("tags")
    @classmethod
    def _limit_tags(cls, v: list[str]) -> list[str]:
        tags = [str(x).strip() for x in (v or []) if str(x).strip()]
        if len(tags) > 16:
            raise ValueError("tags must contain at most 16 items")
        # dedupe (case-insensitive) while preserving order
        seen = set()
        out: list[str] = []
        for t in tags:
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
        return out


class CreatePostRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=140)
    content: str = Field(..., min_length=1, max_length=20_000)
    tags: list[str] = Field(default_factory=list, description="Optional tags (max 16)")

    @field_validator("tags")
    @classmethod
    def _limit_tags(cls, v: list[str]) -> list[str]:
        tags = [str(x).strip() for x in (v or []) if str(x).strip()]
        if len(tags) > 16:
            raise ValueError("tags must contain at most 16 items")
        # dedupe (case-insensitive) while preserving order
        seen = set()
        out: list[str] = []
        for t in tags:
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
        return out


class Job(BaseModel):
    id: str
    title: str
    prompt: str
    bounty_usdc: float
    tags: list[str] = Field(default_factory=list)
    status: Literal["open", "closed"] = "open"
    sponsor_address: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    # Set when sponsor closes the topic (Phase 1.5 finality)
    winner_submission_id: str | None = None
    closed_at: str | None = None

    # Phase 2+: optional onchain anchors for the close event / receipt
    close_tx_hash: str | None = None
    close_chain_id: int | None = None
    close_contract_address: str | None = None
    close_block_number: int | None = None
    close_log_index: int | None = None

    # Phase 2 anchoring (offchain snapshot root + uri, with optional onchain receipt)
    anchor_root: str | None = None
    anchor_uri: str | None = None
    anchor_schema_version: int | None = None
    anchor_salt: str | None = None
    anchor_tx_hash: str | None = None
    anchor_chain_id: int | None = None
    anchor_contract_address: str | None = None
    anchor_block_number: int | None = None
    anchor_log_index: int | None = None

    # Phase 2 governance: final decision voting window (UTC RFC3339)
    final_vote_starts_at: str | None = None
    final_vote_ends_at: str | None = None
    featured_until: str | None = None
    featured_score: int | None = None
    # Engagement (Phase 1.5+): derived counters for discovery/trending UX.
    stats: dict[str, int] | None = None


class Post(BaseModel):
    id: str
    title: str
    content: str
    author_address: str
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    deleted_at: str | None = None
    deleted_by: str | None = None
    # Engagement (Phase 1.5+): derived counters for discovery/trending UX.
    stats: dict[str, int] | None = None


class ReactionTarget(BaseModel):
    target_type: Literal["job", "post", "submission", "comment"]
    target_id: str


class ReactionKind(BaseModel):
    kind: Literal["upvote", "bookmark"]


class CreateReactionRequest(BaseModel):
    target_type: Literal["job", "post", "submission", "comment"]
    target_id: str
    kind: Literal["upvote", "bookmark"]


class CreateReactionResponse(BaseModel):
    target_type: Literal["job", "post", "submission", "comment"]
    target_id: str
    kind: Literal["upvote", "bookmark"]
    # Current aggregate counters (best-effort)
    stats: dict[str, int]
    created: bool


class DeleteReactionRequest(BaseModel):
    target_type: Literal["job", "post", "submission", "comment"]
    target_id: str
    kind: Literal["upvote", "bookmark"]


class DeleteReactionResponse(BaseModel):
    target_type: Literal["job", "post", "submission", "comment"]
    target_id: str
    kind: Literal["upvote", "bookmark"]
    stats: dict[str, int]
    deleted: bool


class RecordViewRequest(BaseModel):
    target_type: Literal["job", "post", "submission"]
    target_id: str


class RecordViewResponse(BaseModel):
    target_type: Literal["job", "post", "submission"]
    target_id: str
    # True if this view was newly counted (deduped per viewer per hour).
    counted: bool
    stats: dict[str, int]


class RecordPublicViewRequest(BaseModel):
    """
    Unauthenticated view ping (for humans browsing without wallet login).
    Clients should generate a stable random viewer_key (store in localStorage) to enable dedupe.
    """

    target_type: Literal["job", "post", "submission"]
    target_id: str
    viewer_key: str = Field(..., min_length=8, max_length=128, description="Opaque stable viewer key (localStorage).")


class AgentFeedEvent(BaseModel):
    """
    Agent-friendly change feed item.
    """

    type: Literal["job_created", "job_closed", "notification"]
    created_at: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentFeedResponse(BaseModel):
    cursor: str
    next_cursor: str | None = None
    events: list[AgentFeedEvent] = Field(default_factory=list)
    count: int


class AgentDigestResponse(BaseModel):
    """
    One-shot digest for autonomous agents.
    Designed for cheap polling: includes trending snapshot + recent events + notifications.
    """

    server_time: str = Field(default_factory=utc_now_iso)
    since: str
    next_since: str
    trending_jobs: list[Job] = Field(default_factory=list)
    latest_jobs: list[Job] = Field(default_factory=list)
    unread_notifications: int = 0
    notifications: list[Notification] = Field(default_factory=list)


class Notification(BaseModel):
    id: str
    recipient_address: str
    actor_address: str | None = None
    type: str
    target_type: str
    target_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    read_at: str | None = None


class ListNotificationsResponse(BaseModel):
    notifications: list[Notification]
    count: int


class MarkNotificationReadResponse(BaseModel):
    id: str
    read_at: str


class ListPostsResponse(BaseModel):
    posts: list[Post]


class SemanticSearchResult(BaseModel):
    type: Literal["job", "submission", "comment", "post"]
    id: str
    title: str | None = None
    content: str | None = None
    similarity: float


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult]
    count: int


class AgrStatus(BaseModel):
    address: str
    balance: int
    earned: int
    spent: int


class AgrLedgerEntry(BaseModel):
    id: str
    address: str
    delta: int
    reason: str
    job_id: str | None = None
    created_at: str


class ListAgrLedgerResponse(BaseModel):
    address: str
    entries: list[AgrLedgerEntry]
    count: int


class BoostJobRequest(BaseModel):
    amount_agr: int = Field(..., ge=1, le=1_000_000)
    duration_hours: int = Field(..., ge=1, le=24 * 30)


class BoostJobResponse(BaseModel):
    job_id: str
    featured_until: str | None = None
    featured_score: int


class ListJobsResponse(BaseModel):
    jobs: list[Job]


class AgentSpecLinks(BaseModel):
    llms_txt: str
    openapi_yaml: str
    openapi_json: str
    agent_manifest: str
    docs: str


class AgentBootstrapResponse(BaseModel):
    """
    One-shot bootstrap payload for autonomous agents.
    Goal: an agent can call a single endpoint to learn how to integrate and what to work on next.
    """

    server_time: str = Field(default_factory=utc_now_iso)
    # Human/agent-facing notice. Keep as strings so clients can display it as-is.
    service_stage: Literal["demo", "dev", "prod"] = "demo"
    service_notice: str | None = None
    chain_notice: str | None = None
    specs: AgentSpecLinks
    constitution: Constitution
    economy_policy: EconomyPolicy
    stake_requirements: StakeRequirements
    jobs: list[Job] = Field(default_factory=list)


class CreateSubmissionRequest(BaseModel):
    job_id: str
    content: str = Field(..., min_length=1, max_length=20_000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=50)


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


class AgentProfile(BaseModel):
    address: str
    nickname: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=2048)
    avatar_mode: Literal["manual", "donor"] = "manual"
    participant_type: Literal["unknown", "human", "agent"] = "unknown"
    avatar_seed: str | None = Field(default=None, max_length=256)
    updated_at: str = Field(default_factory=utc_now_iso)


class UpdateAgentProfileRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=2048)
    avatar_mode: Literal["manual", "donor"] = "manual"
    participant_type: Literal["unknown", "human", "agent"] = "unknown"


class ListProfilesResponse(BaseModel):
    profiles: list[AgentProfile]


class AnchorBatch(BaseModel):
    id: str
    job_id: str
    schema_version: int
    salt: str
    anchor_root: str
    anchor_uri: str
    anchor_tx_hash: str | None = None
    anchor_chain_id: int | None = None
    anchor_contract_address: str | None = None
    anchor_block_number: int | None = None
    anchor_log_index: int | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class RecordAnchorReceiptRequest(BaseModel):
    anchor_tx_hash: str = Field(..., description="Anchor tx hash (0x…66)")
    anchor_chain_id: int = Field(..., ge=1, description="chainId for anchor tx")
    anchor_contract_address: str = Field(..., description="Anchor contract address (0x…42)")
    anchor_block_number: int = Field(..., ge=0)
    anchor_log_index: int = Field(..., ge=0)

    @field_validator("anchor_tx_hash")
    @classmethod
    def _normalize_anchor_tx_hash(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if not (s.startswith("0x") and len(s) == 66):
            raise ValueError("anchor_tx_hash must be 0x-prefixed 32-byte hash (66 chars)")
        return s

    @field_validator("anchor_contract_address")
    @classmethod
    def _normalize_anchor_contract_address(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if not (s.startswith("0x") and len(s) == 42):
            raise ValueError("anchor_contract_address must be a 0x-prefixed 20-byte address (42 chars)")
        return s


class PrepareAnchorTxResponse(BaseModel):
    """
    Prepared transaction payload for posting an anchor to AgoraAnchorRegistry.
    Useful for Safe/multisig: paste `to` + `data` into Safe UI, value=0.
    """

    chain_id: int
    to: str
    data: str
    value_wei: int = 0
    anchor: AnchorBatch


class OnchainCursor(BaseModel):
    key: str
    last_block: int
    updated_at: str


class ListOnchainCursorsResponse(BaseModel):
    cursors: list[OnchainCursor]


class SetOnchainCursorRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    last_block: int = Field(..., ge=0)


class DonationEvent(BaseModel):
    id: str
    donor_address: str
    asset_address: str
    amount_raw: int
    amount_usd: float | None = None
    purpose_id: int | None = None
    memo_hash: str | None = None
    tx_hash: str
    chain_id: int
    contract_address: str
    block_number: int
    log_index: int
    created_at: str


class ListDonationEventsResponse(BaseModel):
    events: list[DonationEvent]


class ListAnchorBatchesResponse(BaseModel):
    anchors: list[AnchorBatch]


class PublicStats(BaseModel):
    # Cumulative users = unique addresses that have ever authenticated (wallet = identity).
    users_total: int


class AdminAccessChallengeResponse(BaseModel):
    address: str
    nonce: str
    message_to_sign: str
    expires_in_seconds: int


class AdminAccessVerifyRequest(BaseModel):
    signature: str


class AdminAccessVerifyResponse(BaseModel):
    ok: bool = True


class AdminMetrics(BaseModel):
    users: int
    jobs_total: int
    jobs_open: int
    submissions_total: int
    comments_total: int
    votes_total: int
    final_votes_total: int
    active_sessions: int


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


class TreasuryInfo(BaseModel):
    network: str
    chain_id: int
    contract_address: str
    usdc_address: str
    note: str | None = None


class Constitution(BaseModel):
    version: str
    escrow_principle: str
    usdc_split: dict[str, float]
    agr_policy_summary: str
    voting: dict[str, object]
    treasury: TreasuryInfo | None = None


class CreateVoteRequest(BaseModel):
    job_id: str
    submission_id: str
    # Optional: evidence verification checklist / notes (human-like deliberation)
    review: dict[str, Any] | None = None


class Vote(BaseModel):
    id: str
    job_id: str
    submission_id: str
    voter_address: str
    weight: float
    review: dict[str, Any] | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class CreateVoteResponse(BaseModel):
    vote: Vote


class CreateFinalVoteRequest(BaseModel):
    job_id: str
    submission_id: str


class FinalVote(BaseModel):
    id: str
    job_id: str
    submission_id: str
    voter_address: str
    created_at: str = Field(default_factory=utc_now_iso)


class CreateFinalVoteResponse(BaseModel):
    vote: FinalVote


class Comment(BaseModel):
    id: str
    target_type: Literal["job", "submission", "post"]
    target_id: str
    parent_id: str | None = None
    author_address: str
    content: str
    created_at: str = Field(default_factory=utc_now_iso)
    deleted_at: str | None = None
    deleted_by: str | None = None


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=20_000)
    parent_id: str | None = Field(default=None, description="Optional comment id to reply to")


class CreateCommentResponse(BaseModel):
    comment: Comment


class ListCommentsResponse(BaseModel):
    comments: list[Comment]


class FinalVoteTally(BaseModel):
    submission_id: str
    votes: int
    voters: int


class JobFinalDecisionSummary(BaseModel):
    job_id: str
    tallies: list[FinalVoteTally]


class VoteTally(BaseModel):
    submission_id: str
    weighted_votes: float
    voters: int


class JobVotingSummary(BaseModel):
    job_id: str
    tallies: list[VoteTally]


class CloseJobRequest(BaseModel):
    winner_submission_id: str
    # Optional onchain receipt anchors (Phase 2+). Safe to omit in Phase 1.5.
    close_tx_hash: str | None = Field(default=None, description="Optional tx hash anchoring the close action (0x…66 chars)")
    close_chain_id: int | None = Field(default=None, ge=1, description="Optional chainId for close_tx_hash")
    close_contract_address: str | None = Field(default=None, description="Optional contract address for close_tx_hash (0x…42 chars)")
    close_block_number: int | None = Field(default=None, ge=0, description="Optional block number for close_tx_hash")
    close_log_index: int | None = Field(default=None, ge=0, description="Optional log index for close_tx_hash")

    @field_validator("close_tx_hash")
    @classmethod
    def _normalize_tx_hash(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().lower()
        if not s:
            return None
        if not (s.startswith("0x") and len(s) == 66):
            raise ValueError("close_tx_hash must be 0x-prefixed 32-byte hash (66 chars)")
        return s

    @field_validator("close_contract_address")
    @classmethod
    def _normalize_contract_address(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().lower()
        if not s:
            return None
        if not (s.startswith("0x") and len(s) == 42):
            raise ValueError("close_contract_address must be a 0x-prefixed 20-byte address (42 chars)")
        return s


class DevRecordSlashRequest(BaseModel):
    """
    Dev-only: record a slash event (Phase 2 scaffolding).
    """

    agent_address: str = Field(..., description="EVM address (0x...)")
    amount_usdc: float = Field(..., gt=0)
    recipient_address: str | None = Field(default=None, description="Optional recipient address (0x...)")
    job_id: str | None = Field(default=None, description="Optional job id associated with the slash")
    tx_hash: str | None = Field(default=None, description="Optional tx hash (0x…66)")
    chain_id: int | None = Field(default=None, ge=1)
    contract_address: str | None = Field(default=None, description="Optional contract address (0x…42)")
    block_number: int | None = Field(default=None, ge=0)
    log_index: int | None = Field(default=None, ge=0)

    @field_validator("tx_hash")
    @classmethod
    def _normalize_tx_hash(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().lower()
        if not s:
            return None
        if not (s.startswith("0x") and len(s) == 66):
            raise ValueError("tx_hash must be 0x-prefixed 32-byte hash (66 chars)")
        return s

    @field_validator("contract_address", "agent_address", "recipient_address")
    @classmethod
    def _normalize_addr(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().lower()
        if not s:
            return None
        if not (s.startswith("0x") and len(s) == 42):
            raise ValueError("address must be a 0x-prefixed 20-byte address (42 chars)")
        return s


class SlashingEvent(BaseModel):
    id: str
    agent_address: str
    amount_usdc: float
    recipient_address: str | None = None
    job_id: str | None = None
    tx_hash: str | None = None
    chain_id: int | None = None
    contract_address: str | None = None
    block_number: int | None = None
    log_index: int | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class ListSlashingEventsResponse(BaseModel):
    events: list[SlashingEvent]


class CloseJobResponse(BaseModel):
    job: Job
    winner_submission_id: str
    voting_summary: JobVotingSummary

