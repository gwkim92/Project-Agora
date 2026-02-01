from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def _now_utc() -> datetime:
    # Used as Python-side fallback; prefer server_default=func.now() where possible.
    return datetime.utcnow()


class JobDB(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    bounty_usdc: Mapped[float] = mapped_column(Float, nullable=False)
    sponsor_address: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )
    winner_submission_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)

    # Phase 2 (onchain evidence) - optional fields to anchor Receipt to chain data.
    close_tx_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    close_chain_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    close_contract_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    close_block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    close_log_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Phase 2 governance: final decision voting window (UTC). Votes are only accepted within this window.
    final_vote_starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    final_vote_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Phase 2 economy: optional offchain "featured" boost (AGR spend) for discovery/curation.
    featured_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    featured_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    submissions: Mapped[List["SubmissionDB"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    votes: Mapped[List["VoteDB"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class SubmissionDB(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    agent_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )

    job: Mapped["JobDB"] = relationship(back_populates="submissions")
    votes: Mapped[List["VoteDB"]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class PostDB(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class SemanticDocDB(Base):
    __tablename__ = "semantic_docs"
    __table_args__ = (
        UniqueConstraint("doc_type", "doc_id", name="uq_semantic_docs_type_id"),
        Index("ix_semantic_docs_type_id", "doc_type", "doc_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    doc_id: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class VoteDB(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("job_id", "voter_address", name="uq_votes_job_voter"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), nullable=False, index=True)
    voter_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    review: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )

    job: Mapped["JobDB"] = relationship(back_populates="votes")
    submission: Mapped["SubmissionDB"] = relationship(back_populates="votes")


class FinalVoteDB(Base):
    __tablename__ = "final_votes"
    __table_args__ = (UniqueConstraint("job_id", "voter_address", name="uq_final_votes_job_voter"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), nullable=False, index=True)
    voter_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class AgentReputationDB(Base):
    __tablename__ = "agent_reputation"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    badges: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class AgentProfileDB(Base):
    __tablename__ = "agent_profiles"

    # Primary identity is still the wallet address.
    address: Mapped[str] = mapped_column(String, primary_key=True)
    nickname: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar_mode: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    participant_type: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class StakeDB(Base):
    __tablename__ = "stakes"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )

    # Phase 2+: optional onchain anchors for the most recent stake update.
    stake_tx_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stake_chain_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stake_contract_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stake_block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stake_log_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class SlashingEventDB(Base):
    __tablename__ = "slashing_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount_usdc: Mapped[float] = mapped_column(Float, nullable=False)
    recipient_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    tx_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chain_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contract_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    log_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class OnchainCursorDB(Base):
    __tablename__ = "onchain_cursors"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    last_block: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class AgrLedgerDB(Base):
    __tablename__ = "agr_ledger"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # positive=credit, negative=debit
    reason: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class JobBoostDB(Base):
    __tablename__ = "job_boosts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount_agr: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    featured_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class AuthChallengeDB(Base):
    __tablename__ = "auth_challenges"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    nonce: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthSessionDB(Base):
    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommentDB(Base):
    __tablename__ = "comments"
    __table_args__ = (
        # For quick reads by target.
        Index("ix_comments_target", "target_type", "target_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    target_type: Mapped[str] = mapped_column(String, nullable=False)  # "job" | "submission" | "post"
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # reply thread
    author_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class DonationEventDB(Base):
    """
    TreasuryVault donation events (idempotent via deterministic id: chain:tx:logIndex).
    """

    __tablename__ = "donation_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    donor_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    asset_address: Mapped[str] = mapped_column(String, nullable=False, index=True)  # address(0)=ETH
    amount_raw: Mapped[int] = mapped_column(BigInteger, nullable=False)  # token raw units (wei, or token decimals)
    amount_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # normalized estimate
    purpose_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memo_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    tx_hash: Mapped[str] = mapped_column(String, nullable=False)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String, nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    log_index: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class DonorTotalDB(Base):
    """
    Cached donation totals by donor address to support quick donor eligibility checks.
    Totals are best-effort and derived from DonationEventDB (USD conversion may be approximate for ETH).
    """

    __tablename__ = "donor_totals"

    donor_address: Mapped[str] = mapped_column(String, primary_key=True)
    total_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    first_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class AnchorBatchDB(Base):
    """
    Offchain snapshot anchoring record for a job (Phase 2).
    Snapshot is created offchain; onchain receipt is recorded after the operator posts a tx.
    """

    __tablename__ = "anchor_batches"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_anchor_batches_job_id"),
        Index("ix_anchor_batches_job_id", "job_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    salt: Mapped[str] = mapped_column(String, nullable=False)  # 0x…64 hex
    anchor_root: Mapped[str] = mapped_column(String, nullable=False)  # 0x…64 hex
    anchor_uri: Mapped[str] = mapped_column(String, nullable=False)

    # Onchain receipt (optional until posted)
    anchor_tx_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    anchor_chain_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    anchor_contract_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    anchor_block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    anchor_log_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now_utc, nullable=False
    )


class AdminAccessChallengeDB(Base):
    """
    Step-up authentication for admin access (separate from login challenges).
    """

    __tablename__ = "admin_access_challenges"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    nonce: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
