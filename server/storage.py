from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from server.config import settings
from server.models import utc_now_iso
from server.db.models import (
    AgrLedgerDB,
    AgentProfileDB,
    AgentReputationDB,
    AnchorBatchDB,
    AuthChallengeDB,
    AdminAccessChallengeDB,
    AuthSessionDB,
    CommentDB,
    DonationEventDB,
    DonorTotalDB,
    FinalVoteDB,
    JobDB,
    JobBoostDB,
    OnchainCursorDB,
    PostDB,
    ReactionDB,
    SemanticDocDB,
    SlashingEventDB,
    StakeDB,
    SubmissionDB,
    ViewEventDB,
    VoteDB,
    NotificationDB,
)
from server.db.session import get_sessionmaker


def _lower_addr(address: str) -> str:
    return address.strip().lower()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _dt_to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    raw = ts.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


class Store(Protocol):
    # ---- Auth: challenges ----
    def create_challenge(self, address: str, message: str, ttl_seconds: int) -> "Challenge": ...
    def set_challenge_message(self, address: str, message: str) -> None: ...
    def get_valid_challenge(self, address: str) -> "Challenge | None": ...
    def consume_challenge(self, address: str) -> None: ...

    # ---- Admin access: step-up challenges ----
    def create_admin_access_challenge(self, address: str, message: str, ttl_seconds: int) -> "Challenge": ...
    def set_admin_access_challenge_message(self, address: str, message: str) -> None: ...
    def get_valid_admin_access_challenge(self, address: str) -> "Challenge | None": ...
    def consume_admin_access_challenge(self, address: str) -> None: ...

    # ---- Auth: sessions ----
    def create_session(self, address: str, ttl_seconds: int) -> "Session": ...
    def get_valid_session(self, token: str) -> "Session | None": ...

    # ---- Stake ----
    def set_stake(
        self,
        address: str,
        amount: float,
        *,
        stake_tx_hash: str | None = None,
        stake_chain_id: int | None = None,
        stake_contract_address: str | None = None,
        stake_block_number: int | None = None,
        stake_log_index: int | None = None,
    ) -> None: ...
    def get_stake(self, address: str) -> float: ...
    def get_stake_meta(self, address: str) -> dict: ...

    # ---- Slashing (Phase 2 scaffold) ----
    def record_slash(self, *, event: dict) -> dict: ...
    def list_slashes(self, *, agent_address: str | None = None, job_id: str | None = None, limit: int = 50) -> list[dict]: ...

    # ---- Onchain cursors ----
    def get_onchain_cursor(self, key: str) -> int | None: ...
    def set_onchain_cursor(self, key: str, last_block: int) -> None: ...
    def list_onchain_cursors(self, *, limit: int = 200) -> list[dict]: ...

    # ---- Jobs/Submissions ----
    def create_job(self, job: dict) -> dict: ...
    def list_jobs(self, *, status: str = "open", tag: str | None = None) -> list[dict]: ...
    def get_job(self, job_id: str) -> dict | None: ...
    def close_job(
        self,
        job_id: str,
        winner_submission_id: str,
        closed_at_iso: str,
        *,
        close_tx_hash: str | None = None,
        close_chain_id: int | None = None,
        close_contract_address: str | None = None,
        close_block_number: int | None = None,
        close_log_index: int | None = None,
    ) -> dict: ...

    def create_submission(self, submission: dict) -> dict: ...
    def get_submission(self, submission_id: str) -> dict | None: ...
    def list_submissions_for_job(self, job_id: str) -> list[dict]: ...

    # ---- Community posts ----
    def create_post(self, post: dict) -> dict: ...
    def list_posts(self, *, tag: str | None = None, limit: int = 50) -> list[dict]: ...
    def get_post(self, post_id: str) -> dict | None: ...

    # ---- Semantic search (optional; behind feature flag) ----
    def upsert_semantic_doc(self, *, doc_type: str, doc_id: str, text: str, embedding: list[float]) -> dict: ...
    def list_semantic_docs(self, *, doc_type: str | None = None, limit: int = 2000) -> list[dict]: ...

    # ---- Discussion (comments) ----
    def create_comment(self, *, comment: dict) -> dict: ...
    def get_comment(self, *, comment_id: str) -> dict | None: ...
    def list_comments(self, *, target_type: str, target_id: str, limit: int = 200) -> list[dict]: ...
    def soft_delete_comment(self, *, comment_id: str, deleted_by: str) -> dict: ...

    # ---- Engagement (reactions/views) ----
    def upsert_reaction(self, *, actor_address: str, target_type: str, target_id: str, kind: str) -> bool: ...
    def delete_reaction(self, *, actor_address: str, target_type: str, target_id: str, kind: str) -> bool: ...
    def record_view(self, *, viewer_address: str, target_type: str, target_id: str) -> bool: ...
    def get_engagement_stats(self, *, target_type: str, target_id: str) -> dict[str, int]: ...
    def get_engagement_stats_batch(self, *, target_type: str, target_ids: list[str]) -> dict[str, dict[str, int]]: ...

    # ---- Notifications ----
    def create_notification(self, *, notification: dict) -> dict: ...
    def list_notifications(self, *, recipient_address: str, unread_only: bool = False, limit: int = 50) -> list[dict]: ...
    def mark_notification_read(self, *, recipient_address: str, notification_id: str) -> dict | None: ...

    # ---- Votes ----
    def upsert_vote(self, *, job_id: str, voter_address: str, vote: dict) -> dict: ...
    def list_votes_for_job(self, job_id: str) -> list[dict]: ...
    def tally_votes_for_job(self, job_id: str) -> dict[str, dict]: ...

    # ---- Final decision votes (Phase 2 governance) ----
    def upsert_final_vote(self, *, job_id: str, voter_address: str, submission_id: str) -> dict: ...
    def list_final_votes_for_job(self, job_id: str) -> list[dict]: ...
    def tally_final_votes_for_job(self, job_id: str) -> dict[str, dict]: ...

    # ---- AGR premium credits (offchain) ----
    def agr_balance(self, address: str) -> dict: ...
    def agr_credit(self, *, address: str, amount: int, reason: str, job_id: str | None = None) -> dict: ...
    def agr_debit(self, *, address: str, amount: int, reason: str, job_id: str | None = None) -> dict: ...
    def boost_job(self, *, job_id: str, address: str, amount_agr: int, duration_seconds: int) -> dict: ...
    def list_agr_ledger(self, *, address: str, limit: int = 50) -> list[dict]: ...

    # ---- Reputation ----
    def ensure_agent_rep(self, address: str) -> dict: ...
    def set_rep_score(self, address: str, score: float) -> dict: ...
    def bump_rep_for_submission(self, address: str, delta: float) -> dict: ...
    def get_rep(self, address: str) -> dict: ...
    def leaderboard(self, limit: int = 50) -> list[dict]: ...

    # ---- Profile ----
    def get_profile(self, address: str) -> dict: ...
    def upsert_profile(
        self, *, address: str, nickname: str | None, avatar_url: str | None, avatar_mode: str, participant_type: str
    ) -> dict: ...
    def get_profiles(self, *, addresses: list[str]) -> list[dict]: ...

    # ---- Donations (TreasuryVault indexing) ----
    def record_donation_event(self, *, event: dict) -> dict: ...
    def get_donor_total(self, address: str) -> dict | None: ...
    def list_donation_events(self, *, limit: int = 50) -> list[dict]: ...

    # ---- Anchoring (offchain snapshot root + onchain receipt) ----
    def upsert_anchor_batch(self, *, job_id: str, anchor_root: str, anchor_uri: str, schema_version: int, salt: str) -> dict: ...
    def get_anchor_batch(self, job_id: str) -> dict | None: ...
    def set_anchor_receipt(
        self,
        *,
        job_id: str,
        anchor_tx_hash: str,
        anchor_chain_id: int,
        anchor_contract_address: str,
        anchor_block_number: int,
        anchor_log_index: int,
    ) -> dict: ...
    def list_anchor_batches(self, *, limit: int = 50) -> list[dict]: ...

    # ---- Admin (operator-only) ----
    def admin_metrics(self) -> dict: ...
    # ---- Public stats ----
    def users_total(self) -> int: ...


@dataclass
class Challenge:
    address: str
    nonce: str
    message: str
    expires_at: float


@dataclass
class Session:
    address: str
    token: str
    expires_at: float


class InMemoryStore:
    def __init__(self) -> None:
        self.challenges_by_address: dict[str, Challenge] = {}
        self.sessions_by_token: dict[str, Session] = {}
        self.stakes_by_address: dict[str, float] = {}
        self.admin_challenges_by_address: dict[str, Challenge] = {}

        self.jobs: dict[str, dict] = {}
        self.submissions: dict[str, dict] = {}
        self.votes: dict[str, dict] = {}
        self.comments: dict[str, dict] = {}
        self.posts: dict[str, dict] = {}
        self.semantic_docs: dict[str, dict] = {}
        self.reputation: dict[str, dict] = {}
        self.profiles: dict[str, dict] = {}
        # Engagement + notifications (best-effort in-memory; used only when DB is unavailable).
        self.reactions: dict[tuple[str, str, str, str], str] = {}  # (actor, type, id, kind) -> created_at_iso
        self.view_events: dict[tuple[str, str, str, str], str] = {}  # (viewer, type, id, window_start_iso) -> created_at_iso
        self.notifications: dict[str, dict] = {}  # id -> notification dict

    # ---- Auth: challenges ----
    def create_challenge(self, address: str, message: str, ttl_seconds: int) -> Challenge:
        addr = _lower_addr(address)
        nonce = secrets.token_hex(16)
        c = Challenge(
            address=addr,
            nonce=nonce,
            message=message,
            expires_at=time.time() + ttl_seconds,
        )
        self.challenges_by_address[addr] = c
        return c

    def set_challenge_message(self, address: str, message: str) -> None:
        addr = _lower_addr(address)
        c = self.challenges_by_address.get(addr)
        if not c:
            return
        self.challenges_by_address[addr] = Challenge(
            address=c.address,
            nonce=c.nonce,
            message=message,
            expires_at=c.expires_at,
        )

    def get_valid_challenge(self, address: str) -> Challenge | None:
        addr = _lower_addr(address)
        c = self.challenges_by_address.get(addr)
        if not c:
            return None
        if c.expires_at < time.time():
            self.challenges_by_address.pop(addr, None)
            return None
        return c

    def consume_challenge(self, address: str) -> None:
        addr = _lower_addr(address)
        self.challenges_by_address.pop(addr, None)

    # ---- Admin access: challenges ----
    def create_admin_access_challenge(self, address: str, message: str, ttl_seconds: int) -> Challenge:
        addr = _lower_addr(address)
        nonce = secrets.token_hex(16)
        c = Challenge(address=addr, nonce=nonce, message=message, expires_at=time.time() + ttl_seconds)
        self.admin_challenges_by_address[addr] = c
        return c

    def set_admin_access_challenge_message(self, address: str, message: str) -> None:
        addr = _lower_addr(address)
        c = self.admin_challenges_by_address.get(addr)
        if not c:
            return
        self.admin_challenges_by_address[addr] = Challenge(address=c.address, nonce=c.nonce, message=message, expires_at=c.expires_at)

    def get_valid_admin_access_challenge(self, address: str) -> Challenge | None:
        addr = _lower_addr(address)
        c = self.admin_challenges_by_address.get(addr)
        if not c:
            return None
        if c.expires_at < time.time():
            self.admin_challenges_by_address.pop(addr, None)
            return None
        return c

    def consume_admin_access_challenge(self, address: str) -> None:
        addr = _lower_addr(address)
        self.admin_challenges_by_address.pop(addr, None)

    # ---- Auth: sessions ----
    def create_session(self, address: str, ttl_seconds: int) -> Session:
        addr = _lower_addr(address)
        token = secrets.token_urlsafe(32)
        s = Session(address=addr, token=token, expires_at=time.time() + ttl_seconds)
        self.sessions_by_token[token] = s
        return s

    def get_valid_session(self, token: str) -> Session | None:
        s = self.sessions_by_token.get(token)
        if not s:
            return None
        if s.expires_at < time.time():
            self.sessions_by_token.pop(token, None)
            return None
        return s

    # ---- Stake ----
    def set_stake(
        self,
        address: str,
        amount: float,
        *,
        stake_tx_hash: str | None = None,
        stake_chain_id: int | None = None,
        stake_contract_address: str | None = None,
        stake_block_number: int | None = None,
        stake_log_index: int | None = None,
    ) -> None:
        addr = _lower_addr(address)
        self.stakes_by_address[addr] = float(amount)
        # store optional meta alongside amount
        meta = self.jobs.get("__stake_meta__", {})
        meta = dict(meta)
        meta[addr] = {
            "stake_tx_hash": stake_tx_hash,
            "stake_chain_id": stake_chain_id,
            "stake_contract_address": stake_contract_address,
            "stake_block_number": stake_block_number,
            "stake_log_index": stake_log_index,
        }
        self.jobs["__stake_meta__"] = meta

    def get_stake(self, address: str) -> float:
        return float(self.stakes_by_address.get(_lower_addr(address), 0.0))

    def get_stake_meta(self, address: str) -> dict:
        addr = _lower_addr(address)
        meta = self.jobs.get("__stake_meta__", {}) or {}
        return dict(meta.get(addr) or {})

    # ---- Slashing (Phase 2 scaffold) ----
    def record_slash(self, *, event: dict) -> dict:
        ev_id = str(uuid.uuid4())
        e = dict(event)
        e["id"] = ev_id
        if not e.get("created_at"):
            e["created_at"] = utc_now_iso()
        slashes = self.jobs.get("__slashing_events__", []) or []
        slashes = list(slashes) + [e]
        self.jobs["__slashing_events__"] = slashes
        return e

    def list_slashes(self, *, agent_address: str | None = None, job_id: str | None = None, limit: int = 50) -> list[dict]:
        slashes = list(self.jobs.get("__slashing_events__", []) or [])
        if agent_address:
            a = _lower_addr(agent_address)
            slashes = [e for e in slashes if _lower_addr(str(e.get("agent_address") or "")) == a]
        if job_id:
            slashes = [e for e in slashes if str(e.get("job_id") or "") == job_id]
        slashes.sort(key=lambda e: str(e.get("created_at") or ""), reverse=True)
        return slashes[: max(1, int(limit))]

    # ---- Onchain cursors ----
    def get_onchain_cursor(self, key: str) -> int | None:
        curs = self.jobs.get("__onchain_cursors__", {}) or {}
        v = curs.get(str(key))
        return int(v) if v is not None else None

    def set_onchain_cursor(self, key: str, last_block: int) -> None:
        curs = self.jobs.get("__onchain_cursors__", {}) or {}
        curs = dict(curs)
        curs[str(key)] = int(last_block)
        self.jobs["__onchain_cursors__"] = curs

    def list_onchain_cursors(self, *, limit: int = 200) -> list[dict]:
        curs = self.jobs.get("__onchain_cursors__", {}) or {}
        if not isinstance(curs, dict):
            return []
        out = []
        for k, v in curs.items():
            out.append({"key": str(k), "last_block": int(v), "updated_at": utc_now_iso()})
        out.sort(key=lambda r: r["key"])
        return out[: max(1, int(limit))]

    # ---- Jobs/Submissions ----
    def create_job(self, job: dict) -> dict:
        job_id = str(uuid.uuid4())
        job = dict(job)
        job["id"] = job_id
        job.setdefault("final_vote_starts_at", None)
        job.setdefault("final_vote_ends_at", None)
        job.setdefault("featured_until", None)
        job.setdefault("featured_score", 0)
        self.jobs[job_id] = job
        return job

    def list_jobs(self, *, status: str = "open", tag: str | None = None) -> list[dict]:
        """
        status: 'open' or 'all'
        tag: optional tag filter
        """
        jobs = list(self.jobs.values())
        # featured first
        def _k(j: dict):
            fu = j.get("featured_until") or ""
            fs = int(j.get("featured_score") or 0)
            ca = j.get("created_at", "") or ""
            return (fu, fs, ca)
        jobs.sort(key=_k, reverse=True)

        if status != "all":
            jobs = [j for j in jobs if j.get("status") == "open"]

        if tag:
            t = tag.strip().lower()
            jobs = [j for j in jobs if any(str(x).lower() == t for x in (j.get("tags") or []))]

        return jobs

    # ---- Community posts ----
    def create_post(self, post: dict) -> dict:
        post_id = str(uuid.uuid4())
        p = dict(post)
        p["id"] = post_id
        p["created_at"] = p.get("created_at") or utc_now_iso()
        p["author_address"] = _lower_addr(str(p.get("author_address") or ""))
        p["tags"] = list(p.get("tags") or [])
        p.setdefault("deleted_at", None)
        p.setdefault("deleted_by", None)
        self.posts[post_id] = p
        return dict(p)

    def list_posts(self, *, tag: str | None = None, limit: int = 50) -> list[dict]:
        out = [p for p in self.posts.values() if not p.get("deleted_at")]
        out.sort(key=lambda p: str(p.get("created_at") or ""), reverse=True)
        if tag:
            t = tag.strip().lower()
            out = [p for p in out if any(str(x).lower() == t for x in (p.get("tags") or []))]
        return out[: max(1, int(limit))]

    def get_post(self, post_id: str) -> dict | None:
        p = self.posts.get(str(post_id))
        if not p:
            return None
        if p.get("deleted_at"):
            return None
        return dict(p)

    # ---- Semantic search (optional) ----
    def upsert_semantic_doc(self, *, doc_type: str, doc_id: str, text: str, embedding: list[float]) -> dict:
        key = f"{str(doc_type)}:{str(doc_id)}"
        row = {
            "id": self.semantic_docs.get(key, {}).get("id") or str(uuid.uuid4()),
            "doc_type": str(doc_type),
            "doc_id": str(doc_id),
            "text": str(text),
            "embedding": list(embedding or []),
            "updated_at": utc_now_iso(),
        }
        self.semantic_docs[key] = row
        return dict(row)

    def list_semantic_docs(self, *, doc_type: str | None = None, limit: int = 2000) -> list[dict]:
        rows = list(self.semantic_docs.values())
        if doc_type:
            rows = [r for r in rows if str(r.get("doc_type") or "") == str(doc_type)]
        rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
        return rows[: max(1, int(limit))]

    # ---- AGR credits (offchain) ----
    def _agr_store(self) -> dict:
        store = self.jobs.get("__agr_ledger__", {})
        if not isinstance(store, list):
            store = []
        return {"ledger": store}

    def agr_balance(self, address: str) -> dict:
        addr = _lower_addr(address)
        ledger = (self.jobs.get("__agr_ledger__", []) or [])
        earned = sum(int(x.get("delta") or 0) for x in ledger if _lower_addr(str(x.get("address") or "")) == addr and int(x.get("delta") or 0) > 0)
        spent = -sum(int(x.get("delta") or 0) for x in ledger if _lower_addr(str(x.get("address") or "")) == addr and int(x.get("delta") or 0) < 0)
        return {"address": addr, "earned": int(earned), "spent": int(spent), "balance": int(earned - spent)}

    def agr_credit(self, *, address: str, amount: int, reason: str, job_id: str | None = None) -> dict:
        addr = _lower_addr(address)
        amt = int(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        row = {"id": str(uuid.uuid4()), "address": addr, "delta": amt, "reason": reason, "job_id": job_id, "created_at": utc_now_iso()}
        ledger = list(self.jobs.get("__agr_ledger__", []) or [])
        ledger.append(row)
        self.jobs["__agr_ledger__"] = ledger
        return row

    def agr_debit(self, *, address: str, amount: int, reason: str, job_id: str | None = None) -> dict:
        addr = _lower_addr(address)
        amt = int(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        bal = self.agr_balance(addr)["balance"]
        if bal < amt:
            raise ValueError("insufficient AGR balance")
        row = {"id": str(uuid.uuid4()), "address": addr, "delta": -amt, "reason": reason, "job_id": job_id, "created_at": utc_now_iso()}
        ledger = list(self.jobs.get("__agr_ledger__", []) or [])
        ledger.append(row)
        self.jobs["__agr_ledger__"] = ledger
        return row

    def boost_job(self, *, job_id: str, address: str, amount_agr: int, duration_seconds: int) -> dict:
        # debit first
        self.agr_debit(address=address, amount=int(amount_agr), reason="job_boost", job_id=job_id)
        job = self.jobs.get(job_id)
        if not job:
            raise KeyError("Job not found")
        now = utc_now_iso()
        # compute featured_until as max(existing, now) + duration
        base = job.get("featured_until") or now
        try:
            import datetime as _dt
            b = _dt.datetime.fromisoformat(str(base).replace("Z", "+00:00"))
            end = b + _dt.timedelta(seconds=int(duration_seconds))
            featured_until = end.isoformat().replace("+00:00", "Z")
        except Exception:
            featured_until = now
        job = dict(job)
        job["featured_until"] = featured_until
        job["featured_score"] = int(job.get("featured_score") or 0) + int(amount_agr)
        self.jobs[job_id] = job
        return {"job_id": job_id, "featured_until": featured_until, "featured_score": job["featured_score"]}

    def list_agr_ledger(self, *, address: str, limit: int = 50) -> list[dict]:
        addr = _lower_addr(address)
        lim = max(1, int(limit))
        ledger = list(self.jobs.get("__agr_ledger__", []) or [])
        rows = [x for x in ledger if _lower_addr(str(x.get("address") or "")) == addr]
        rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return rows[:lim]

    def get_job(self, job_id: str) -> dict | None:
        return self.jobs.get(job_id)

    def close_job(
        self,
        job_id: str,
        winner_submission_id: str,
        closed_at_iso: str,
        *,
        close_tx_hash: str | None = None,
        close_chain_id: int | None = None,
        close_contract_address: str | None = None,
        close_block_number: int | None = None,
        close_log_index: int | None = None,
    ) -> dict:
        job = self.jobs.get(job_id)
        if not job:
            raise KeyError("Job not found")
        job = dict(job)
        job["status"] = "closed"
        job["winner_submission_id"] = winner_submission_id
        job["closed_at"] = closed_at_iso
        job["close_tx_hash"] = close_tx_hash
        job["close_chain_id"] = close_chain_id
        job["close_contract_address"] = close_contract_address
        job["close_block_number"] = close_block_number
        job["close_log_index"] = close_log_index
        self.jobs[job_id] = job
        return job

    def create_submission(self, submission: dict) -> dict:
        sub_id = str(uuid.uuid4())
        submission = dict(submission)
        submission["id"] = sub_id
        self.submissions[sub_id] = submission
        return submission

    def get_submission(self, submission_id: str) -> dict | None:
        return self.submissions.get(str(submission_id))

    def list_submissions_for_job(self, job_id: str) -> list[dict]:
        subs = [s for s in self.submissions.values() if s.get("job_id") == job_id]
        subs.sort(key=lambda s: s.get("created_at", ""), reverse=False)
        return subs

    # ---- Discussion (comments) ----
    def create_comment(self, *, comment: dict) -> dict:
        cid = str(uuid.uuid4())
        c = dict(comment)
        c["id"] = cid
        c["created_at"] = c.get("created_at") or utc_now_iso()
        c["author_address"] = _lower_addr(str(c.get("author_address") or ""))
        self.comments[cid] = c
        return c

    def get_comment(self, *, comment_id: str) -> dict | None:
        return self.comments.get(str(comment_id))

    def list_comments(self, *, target_type: str, target_id: str, limit: int = 200) -> list[dict]:
        t = str(target_type)
        tid = str(target_id)
        out = [c for c in self.comments.values() if c.get("target_type") == t and c.get("target_id") == tid]
        out.sort(key=lambda c: c.get("created_at", ""), reverse=False)
        return out[: int(limit)]

    def soft_delete_comment(self, *, comment_id: str, deleted_by: str) -> dict:
        cid = str(comment_id)
        row = self.comments.get(cid)
        if not row:
            raise KeyError("Comment not found")
        if row.get("deleted_at"):
            return row
        row = dict(row)
        row["deleted_at"] = utc_now_iso()
        row["deleted_by"] = _lower_addr(deleted_by)
        self.comments[cid] = row
        return row

    # ---- Engagement (reactions/views) ----
    def upsert_reaction(self, *, actor_address: str, target_type: str, target_id: str, kind: str) -> bool:
        key = (_lower_addr(actor_address), str(target_type), str(target_id), str(kind))
        if key in self.reactions:
            return False
        self.reactions[key] = utc_now_iso()
        return True

    def delete_reaction(self, *, actor_address: str, target_type: str, target_id: str, kind: str) -> bool:
        key = (_lower_addr(actor_address), str(target_type), str(target_id), str(kind))
        if key not in self.reactions:
            return False
        del self.reactions[key]
        return True

    def record_view(self, *, viewer_address: str, target_type: str, target_id: str) -> bool:
        # Dedup per viewer per hour.
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        window = now.isoformat().replace("+00:00", "Z")
        key = (_lower_addr(viewer_address), str(target_type), str(target_id), window)
        if key in self.view_events:
            return False
        self.view_events[key] = utc_now_iso()
        return True

    def get_engagement_stats(self, *, target_type: str, target_id: str) -> dict[str, int]:
        return (self.get_engagement_stats_batch(target_type=target_type, target_ids=[str(target_id)]) or {}).get(str(target_id), {})

    def get_engagement_stats_batch(self, *, target_type: str, target_ids: list[str]) -> dict[str, dict[str, int]]:
        t = str(target_type)
        ids = [str(x) for x in (target_ids or []) if str(x)]
        out: dict[str, dict[str, int]] = {}
        for tid in ids:
            up = sum(1 for (a, tt, i, k) in self.reactions.keys() if tt == t and i == tid and k == "upvote")
            bm = sum(1 for (a, tt, i, k) in self.reactions.keys() if tt == t and i == tid and k == "bookmark")
            vw = sum(1 for (a, tt, i, w) in self.view_events.keys() if tt == t and i == tid)
            cm = sum(
                1
                for c in self.comments.values()
                if c.get("target_type") == t and c.get("target_id") == tid and not c.get("deleted_at")
            )
            out[tid] = {"upvotes": int(up), "bookmarks": int(bm), "views": int(vw), "comments": int(cm)}
        return out

    # ---- Notifications ----
    def create_notification(self, *, notification: dict) -> dict:
        nid = str(uuid.uuid4())
        n = dict(notification)
        n["id"] = nid
        n["recipient_address"] = _lower_addr(str(n.get("recipient_address") or ""))
        n["actor_address"] = _lower_addr(str(n.get("actor_address") or "")) if n.get("actor_address") else None
        n["created_at"] = n.get("created_at") or utc_now_iso()
        self.notifications[nid] = n
        return n

    def list_notifications(self, *, recipient_address: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
        addr = _lower_addr(recipient_address)
        rows = [n for n in self.notifications.values() if _lower_addr(str(n.get("recipient_address") or "")) == addr]
        if unread_only:
            rows = [n for n in rows if not n.get("read_at")]
        rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return rows[: max(1, int(limit))]

    def mark_notification_read(self, *, recipient_address: str, notification_id: str) -> dict | None:
        addr = _lower_addr(recipient_address)
        nid = str(notification_id)
        row = self.notifications.get(nid)
        if not row:
            return None
        if _lower_addr(str(row.get("recipient_address") or "")) != addr:
            return None
        if row.get("read_at"):
            return row
        row = dict(row)
        row["read_at"] = utc_now_iso()
        self.notifications[nid] = row
        return row

    # ---- Votes ----
    def upsert_vote(self, *, job_id: str, voter_address: str, vote: dict) -> dict:
        """
        One vote per (job_id, voter). If voter revotes, overwrite the existing one (same id).
        """
        key = f"{job_id}:{_lower_addr(voter_address)}"
        existing_id = None
        for vid, v in self.votes.items():
            if v.get("_key") == key:
                existing_id = vid
                break

        if existing_id:
            v = dict(vote)
            v["id"] = existing_id
            v["_key"] = key
            self.votes[existing_id] = v
            return v

        vote_id = str(uuid.uuid4())
        v = dict(vote)
        v["id"] = vote_id
        v["_key"] = key
        self.votes[vote_id] = v
        return v

    def list_votes_for_job(self, job_id: str) -> list[dict]:
        vs = [v for v in self.votes.values() if v.get("job_id") == job_id]
        vs.sort(key=lambda v: v.get("created_at", ""), reverse=False)
        return vs

    def tally_votes_for_job(self, job_id: str) -> dict[str, dict]:
        """
        Returns dict submission_id -> {weighted_votes, voters}
        """
        tallies: dict[str, dict] = {}
        for v in self.list_votes_for_job(job_id):
            sid = v.get("submission_id")
            if not sid:
                continue
            if sid not in tallies:
                tallies[sid] = {"submission_id": sid, "weighted_votes": 0.0, "voters": 0}
            tallies[sid]["weighted_votes"] += float(v.get("weight", 1.0))
            tallies[sid]["voters"] += 1
        return tallies

    # ---- Final decision votes ----
    def upsert_final_vote(self, *, job_id: str, voter_address: str, submission_id: str) -> dict:
        if "__final_votes__" not in self.jobs:
            self.jobs["__final_votes__"] = {}
        store = self.jobs["__final_votes__"]
        if not isinstance(store, dict):
            store = {}
        key = f"{job_id}:{_lower_addr(voter_address)}"
        vote_id = str(uuid.uuid4())
        v = {
            "id": vote_id,
            "job_id": job_id,
            "submission_id": submission_id,
            "voter_address": _lower_addr(voter_address),
            "created_at": utc_now_iso(),
            "_key": key,
        }
        # overwrite by key
        store[key] = v
        self.jobs["__final_votes__"] = store
        return v

    def list_final_votes_for_job(self, job_id: str) -> list[dict]:
        store = self.jobs.get("__final_votes__", {}) or {}
        votes = [v for v in store.values() if v.get("job_id") == job_id]
        votes.sort(key=lambda v: v.get("created_at", ""), reverse=False)
        return votes

    def tally_final_votes_for_job(self, job_id: str) -> dict[str, dict]:
        votes = self.list_final_votes_for_job(job_id)
        tallies: dict[str, dict] = {}
        for v in votes:
            sid = str(v.get("submission_id") or "")
            if not sid:
                continue
            t = tallies.get(sid) or {"submission_id": sid, "votes": 0, "voters": 0}
            t["votes"] = int(t.get("votes", 0)) + 1
            t["voters"] = int(t.get("voters", 0)) + 1
            tallies[sid] = t
        return tallies

    # ---- Reputation (MVP heuristic) ----
    def ensure_agent_rep(self, address: str) -> dict:
        addr = _lower_addr(address)
        if addr not in self.reputation:
            self.reputation[addr] = {
                "address": addr,
                "score": 0.0,
                "level": 1,
                "wins": 0,
                "losses": 0,
                "badges": [],
                "last_updated_at": "",
            }
        return self.reputation[addr]

    def set_rep_score(self, address: str, score: float) -> dict:
        rep = self.ensure_agent_rep(address)
        rep["score"] = float(score)
        rep["level"] = max(1, int(rep["score"] // 100) + 1)
        return rep

    def bump_rep_for_submission(self, address: str, delta: float) -> dict:
        rep = self.ensure_agent_rep(address)
        rep["score"] = float(rep.get("score", 0.0)) + float(delta)
        rep["level"] = max(1, int(rep["score"] // 100) + 1)
        return rep

    def get_rep(self, address: str) -> dict:
        return self.ensure_agent_rep(address)

    def leaderboard(self, limit: int = 50) -> list[dict]:
        entries = list(self.reputation.values())
        entries.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
        return entries[:limit]

    # ---- Profile ----
    def get_profile(self, address: str) -> dict:
        addr = _lower_addr(address)
        row = self.profiles.get(addr)
        if row:
            out = dict(row)
        else:
            out = {
            "address": addr,
            "nickname": None,
            "avatar_url": None,
            "avatar_mode": "manual",
            "participant_type": "unknown",
            "updated_at": utc_now_iso(),
            }

        if (out.get("avatar_mode") or "manual") == "donor":
            t = self.get_donor_total(addr) or {}
            first_id = t.get("first_event_id")
            out["avatar_seed"] = f"{addr}:{first_id}" if first_id else addr
        return out

    def upsert_profile(
        self, *, address: str, nickname: str | None, avatar_url: str | None, avatar_mode: str, participant_type: str
    ) -> dict:
        addr = _lower_addr(address)
        row = {
            "address": addr,
            "nickname": nickname,
            "avatar_url": avatar_url,
            "avatar_mode": avatar_mode,
            "participant_type": participant_type or "unknown",
            "updated_at": utc_now_iso(),
        }
        self.profiles[addr] = row
        return dict(row)

    def get_profiles(self, *, addresses: list[str]) -> list[dict]:
        out: list[dict] = []
        for a in addresses or []:
            addr = _lower_addr(str(a))
            out.append(self.get_profile(addr))
        return out

    # ---- Donations ----
    def record_donation_event(self, *, event: dict) -> dict:
        ev_id = str(event.get("id") or "")
        if not ev_id:
            raise ValueError("donation event missing id")
        store = self.jobs.get("__donation_events__", {}) or {}
        if not isinstance(store, dict):
            store = {}
        if ev_id in store:
            return dict(store[ev_id])

        e = dict(event)
        e["id"] = ev_id
        e.setdefault("created_at", utc_now_iso())
        e["donor_address"] = _lower_addr(str(e.get("donor_address") or ""))
        e["asset_address"] = _lower_addr(str(e.get("asset_address") or ""))
        e["contract_address"] = _lower_addr(str(e.get("contract_address") or ""))
        e["tx_hash"] = str(e.get("tx_hash") or "").lower()
        e["chain_id"] = int(e.get("chain_id") or 0)
        e["block_number"] = int(e.get("block_number") or 0)
        e["log_index"] = int(e.get("log_index") or 0)
        e["amount_raw"] = int(e.get("amount_raw") or 0)
        if e.get("amount_usd") is not None:
            e["amount_usd"] = float(e.get("amount_usd") or 0.0)
        store[ev_id] = e
        self.jobs["__donation_events__"] = store

        # donor totals + eligibility
        donor = e["donor_address"]
        amount_usd = e.get("amount_usd")
        totals = self.jobs.get("__donor_totals__", {}) or {}
        if not isinstance(totals, dict):
            totals = {}
        row = dict(totals.get(donor) or {"donor_address": donor, "total_usd": 0.0, "first_event_id": None, "updated_at": utc_now_iso()})
        if not row.get("first_event_id"):
            row["first_event_id"] = ev_id
        if amount_usd is not None:
            row["total_usd"] = float(row.get("total_usd") or 0.0) + float(amount_usd)
        row["updated_at"] = utc_now_iso()
        totals[donor] = row
        self.jobs["__donor_totals__"] = totals

        # Auto-enable donor avatar mode if threshold is reached.
        try:
            if float(row.get("total_usd") or 0.0) >= float(getattr(settings, "DONOR_THRESHOLD_USD", 10.0)):
                p = self.get_profile(donor)
                # Keep nickname; clear avatar_url; lock to donor mode.
                self.upsert_profile(address=donor, nickname=p.get("nickname"), avatar_url=None, avatar_mode="donor")
        except Exception:
            pass

        return dict(e)

    def get_donor_total(self, address: str) -> dict | None:
        addr = _lower_addr(address)
        totals = self.jobs.get("__donor_totals__", {}) or {}
        if not isinstance(totals, dict):
            return None
        row = totals.get(addr)
        return dict(row) if row else None

    def list_donation_events(self, *, limit: int = 50) -> list[dict]:
        store = self.jobs.get("__donation_events__", {}) or {}
        if not isinstance(store, dict):
            return []
        rows = list(store.values())
        rows.sort(key=lambda e: (int(e.get("block_number") or 0), int(e.get("log_index") or 0)), reverse=True)
        return [dict(r) for r in rows[: max(1, int(limit))]]

    # ---- Anchoring ----
    def upsert_anchor_batch(self, *, job_id: str, anchor_root: str, anchor_uri: str, schema_version: int, salt: str) -> dict:
        jid = str(job_id)
        store = self.jobs.get("__anchor_batches__", {}) or {}
        if not isinstance(store, dict):
            store = {}
        existing = store.get(jid)
        if existing:
            return dict(existing)
        row = {
            "id": str(uuid.uuid4()),
            "job_id": jid,
            "schema_version": int(schema_version),
            "salt": str(salt),
            "anchor_root": str(anchor_root),
            "anchor_uri": str(anchor_uri),
            "anchor_tx_hash": None,
            "anchor_chain_id": None,
            "anchor_contract_address": None,
            "anchor_block_number": None,
            "anchor_log_index": None,
            "created_at": utc_now_iso(),
        }
        store[jid] = row
        self.jobs["__anchor_batches__"] = store
        return dict(row)

    def get_anchor_batch(self, job_id: str) -> dict | None:
        jid = str(job_id)
        store = self.jobs.get("__anchor_batches__", {}) or {}
        if not isinstance(store, dict):
            return None
        row = store.get(jid)
        return dict(row) if row else None

    def list_anchor_batches(self, *, limit: int = 50) -> list[dict]:
        store = self.jobs.get("__anchor_batches__", {}) or {}
        if not isinstance(store, dict):
            return []
        rows = list(store.values())
        rows.sort(key=lambda a: str(a.get("created_at") or ""), reverse=True)
        return [dict(r) for r in rows[: max(1, int(limit))]]

    def set_anchor_receipt(
        self,
        *,
        job_id: str,
        anchor_tx_hash: str,
        anchor_chain_id: int,
        anchor_contract_address: str,
        anchor_block_number: int,
        anchor_log_index: int,
    ) -> dict:
        jid = str(job_id)
        store = self.jobs.get("__anchor_batches__", {}) or {}
        if not isinstance(store, dict):
            store = {}
        row = store.get(jid)
        if not row:
            raise KeyError("Anchor batch not found for job")
        row = dict(row)
        row["anchor_tx_hash"] = str(anchor_tx_hash).lower()
        row["anchor_chain_id"] = int(anchor_chain_id)
        row["anchor_contract_address"] = _lower_addr(str(anchor_contract_address))
        row["anchor_block_number"] = int(anchor_block_number)
        row["anchor_log_index"] = int(anchor_log_index)
        store[jid] = row
        self.jobs["__anchor_batches__"] = store
        return dict(row)

    # ---- Admin ----
    def admin_metrics(self) -> dict:
        users = set(self.reputation.keys()) | {s.address for s in self.sessions_by_token.values()}
        jobs_total = len([k for k in self.jobs.keys() if k and not k.startswith("__")])
        jobs_open = len([j for j in self.jobs.values() if isinstance(j, dict) and j.get("status") == "open"])
        return {
            "users": len(users),
            "jobs_total": jobs_total,
            "jobs_open": jobs_open,
            "submissions_total": len(self.submissions),
            "comments_total": len(self.comments),
            "votes_total": len(self.votes),
            "final_votes_total": len((self.jobs.get("__final_votes__", {}) or {}).keys()),
            "active_sessions": len(self.sessions_by_token),
        }

    def users_total(self) -> int:
        # Cumulative users = addresses that have ever authenticated (ensure_agent_rep on verify).
        return int(len(self.reputation.keys()))


class PostgresStore:
    """
    Phase 1.5: DB-backed store. Keeps the API-facing dict shape identical to InMemoryStore.
    """

    def __init__(self) -> None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set (required for PostgresStore)")
        self._SessionLocal = get_sessionmaker()

    def _session(self) -> Session:
        return self._SessionLocal()

    # ---- Auth: challenges ----
    def create_challenge(self, address: str, message: str, ttl_seconds: int) -> Challenge:
        addr = _lower_addr(address)
        nonce = secrets.token_hex(16)
        expires_at_ts = time.time() + int(ttl_seconds)
        expires_at_dt = datetime.fromtimestamp(expires_at_ts, tz=timezone.utc)

        with self._session() as db:
            # Use an upsert to avoid race conditions when multiple callers request a challenge for the same address.
            stmt = pg_insert(AuthChallengeDB).values(
                address=addr,
                nonce=nonce,
                message=message,
                expires_at=expires_at_dt,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[AuthChallengeDB.address],
                set_={"nonce": nonce, "message": message, "expires_at": expires_at_dt},
            )
            db.execute(stmt)
            db.commit()

        return Challenge(address=addr, nonce=nonce, message=message, expires_at=expires_at_ts)

    def set_challenge_message(self, address: str, message: str) -> None:
        addr = _lower_addr(address)
        with self._session() as db:
            db.execute(update(AuthChallengeDB).where(AuthChallengeDB.address == addr).values(message=message))
            db.commit()

    def get_valid_challenge(self, address: str) -> Challenge | None:
        addr = _lower_addr(address)
        now_ts = time.time()
        with self._session() as db:
            row = db.get(AuthChallengeDB, addr)
            if not row:
                return None
            expires_ts = row.expires_at.replace(tzinfo=timezone.utc).timestamp()
            if expires_ts < now_ts:
                db.execute(delete(AuthChallengeDB).where(AuthChallengeDB.address == addr))
                db.commit()
                return None
            return Challenge(address=row.address, nonce=row.nonce, message=row.message, expires_at=expires_ts)

    def consume_challenge(self, address: str) -> None:
        addr = _lower_addr(address)
        with self._session() as db:
            db.execute(delete(AuthChallengeDB).where(AuthChallengeDB.address == addr))
            db.commit()

    # ---- Admin access: challenges ----
    def create_admin_access_challenge(self, address: str, message: str, ttl_seconds: int) -> Challenge:
        addr = _lower_addr(address)
        nonce = secrets.token_hex(16)
        expires_at_ts = time.time() + int(ttl_seconds)
        expires_at_dt = datetime.fromtimestamp(expires_at_ts, tz=timezone.utc)

        with self._session() as db:
            row = db.get(AdminAccessChallengeDB, addr)
            if row:
                row.nonce = nonce
                row.message = message
                row.expires_at = expires_at_dt
            else:
                db.add(AdminAccessChallengeDB(address=addr, nonce=nonce, message=message, expires_at=expires_at_dt))
            db.commit()

        return Challenge(address=addr, nonce=nonce, message=message, expires_at=expires_at_ts)

    def set_admin_access_challenge_message(self, address: str, message: str) -> None:
        addr = _lower_addr(address)
        with self._session() as db:
            db.execute(update(AdminAccessChallengeDB).where(AdminAccessChallengeDB.address == addr).values(message=message))
            db.commit()

    def get_valid_admin_access_challenge(self, address: str) -> Challenge | None:
        addr = _lower_addr(address)
        now_ts = time.time()
        with self._session() as db:
            row = db.get(AdminAccessChallengeDB, addr)
            if not row:
                return None
            expires_ts = row.expires_at.replace(tzinfo=timezone.utc).timestamp()
            if expires_ts < now_ts:
                db.execute(delete(AdminAccessChallengeDB).where(AdminAccessChallengeDB.address == addr))
                db.commit()
                return None
            return Challenge(address=row.address, nonce=row.nonce, message=row.message, expires_at=expires_ts)

    def consume_admin_access_challenge(self, address: str) -> None:
        addr = _lower_addr(address)
        with self._session() as db:
            db.execute(delete(AdminAccessChallengeDB).where(AdminAccessChallengeDB.address == addr))
            db.commit()

    # ---- Auth: sessions ----
    def create_session(self, address: str, ttl_seconds: int) -> Session:
        addr = _lower_addr(address)
        token = secrets.token_urlsafe(32)
        expires_at_ts = time.time() + int(ttl_seconds)
        expires_at_dt = datetime.fromtimestamp(expires_at_ts, tz=timezone.utc)

        with self._session() as db:
            db.add(AuthSessionDB(token=token, address=addr, expires_at=expires_at_dt))
            db.commit()
        return Session(address=addr, token=token, expires_at=expires_at_ts)

    def get_valid_session(self, token: str) -> Session | None:
        now_ts = time.time()
        with self._session() as db:
            row = db.get(AuthSessionDB, token)
            if not row:
                return None
            expires_ts = row.expires_at.replace(tzinfo=timezone.utc).timestamp()
            if expires_ts < now_ts:
                db.execute(delete(AuthSessionDB).where(AuthSessionDB.token == token))
                db.commit()
                return None
            return Session(address=row.address, token=row.token, expires_at=expires_ts)

    # ---- Stake ----
    def set_stake(
        self,
        address: str,
        amount: float,
        *,
        stake_tx_hash: str | None = None,
        stake_chain_id: int | None = None,
        stake_contract_address: str | None = None,
        stake_block_number: int | None = None,
        stake_log_index: int | None = None,
    ) -> None:
        addr = _lower_addr(address)
        with self._session() as db:
            row = db.get(StakeDB, addr)
            if row:
                row.amount = float(amount)
                row.updated_at = _now_utc()
                row.stake_tx_hash = stake_tx_hash
                row.stake_chain_id = int(stake_chain_id) if stake_chain_id is not None else None
                row.stake_contract_address = stake_contract_address
                row.stake_block_number = int(stake_block_number) if stake_block_number is not None else None
                row.stake_log_index = int(stake_log_index) if stake_log_index is not None else None
            else:
                db.add(
                    StakeDB(
                        address=addr,
                        amount=float(amount),
                        updated_at=_now_utc(),
                        stake_tx_hash=stake_tx_hash,
                        stake_chain_id=int(stake_chain_id) if stake_chain_id is not None else None,
                        stake_contract_address=stake_contract_address,
                        stake_block_number=int(stake_block_number) if stake_block_number is not None else None,
                        stake_log_index=int(stake_log_index) if stake_log_index is not None else None,
                    )
                )
            db.commit()

    def get_stake(self, address: str) -> float:
        addr = _lower_addr(address)
        with self._session() as db:
            row = db.get(StakeDB, addr)
            return float(row.amount) if row else 0.0

    def get_stake_meta(self, address: str) -> dict:
        addr = _lower_addr(address)
        with self._session() as db:
            row = db.get(StakeDB, addr)
            if not row:
                return {}
            return {
                "stake_tx_hash": row.stake_tx_hash,
                "stake_chain_id": int(row.stake_chain_id) if row.stake_chain_id is not None else None,
                "stake_contract_address": row.stake_contract_address,
                "stake_block_number": int(row.stake_block_number) if row.stake_block_number is not None else None,
                "stake_log_index": int(row.stake_log_index) if row.stake_log_index is not None else None,
            }

    # ---- Slashing (Phase 2 scaffold) ----
    def _slash_to_dict(self, e: SlashingEventDB) -> dict:
        return {
            "id": e.id,
            "agent_address": e.agent_address,
            "amount_usdc": float(e.amount_usdc),
            "recipient_address": e.recipient_address,
            "job_id": e.job_id,
            "tx_hash": e.tx_hash,
            "chain_id": int(e.chain_id) if e.chain_id is not None else None,
            "contract_address": e.contract_address,
            "block_number": int(e.block_number) if e.block_number is not None else None,
            "log_index": int(e.log_index) if e.log_index is not None else None,
            "created_at": _dt_to_iso(e.created_at),
        }

    def record_slash(self, *, event: dict) -> dict:
        ev_id = str(event.get("id") or uuid.uuid4())
        created_at = _parse_iso(str(event.get("created_at") or "")) or _now_utc()
        row = SlashingEventDB(
            id=ev_id,
            agent_address=_lower_addr(str(event.get("agent_address") or "")),
            amount_usdc=float(event.get("amount_usdc") or 0.0),
            recipient_address=_lower_addr(str(event.get("recipient_address") or "")) if event.get("recipient_address") else None,
            job_id=str(event.get("job_id")) if event.get("job_id") else None,
            tx_hash=str(event.get("tx_hash")) if event.get("tx_hash") else None,
            chain_id=int(event.get("chain_id")) if event.get("chain_id") is not None else None,
            contract_address=_lower_addr(str(event.get("contract_address") or "")) if event.get("contract_address") else None,
            block_number=int(event.get("block_number")) if event.get("block_number") is not None else None,
            log_index=int(event.get("log_index")) if event.get("log_index") is not None else None,
            created_at=created_at,
        )
        with self._session() as db:
            existing = db.get(SlashingEventDB, ev_id)
            if existing:
                return self._slash_to_dict(existing)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._slash_to_dict(row)

    def list_slashes(self, *, agent_address: str | None = None, job_id: str | None = None, limit: int = 50) -> list[dict]:
        with self._session() as db:
            q = select(SlashingEventDB).order_by(SlashingEventDB.created_at.desc())
            if agent_address:
                q = q.where(SlashingEventDB.agent_address == _lower_addr(agent_address))
            if job_id:
                q = q.where(SlashingEventDB.job_id == job_id)
            q = q.limit(max(1, int(limit)))
            rows = list(db.execute(q).scalars().all())
        return [self._slash_to_dict(r) for r in rows]

    # ---- Onchain cursors ----
    def get_onchain_cursor(self, key: str) -> int | None:
        with self._session() as db:
            row = db.get(OnchainCursorDB, key)
            return int(row.last_block) if row else None

    def set_onchain_cursor(self, key: str, last_block: int) -> None:
        with self._session() as db:
            row = db.get(OnchainCursorDB, key)
            if row:
                row.last_block = int(last_block)
                row.updated_at = _now_utc()
            else:
                db.add(OnchainCursorDB(key=key, last_block=int(last_block), updated_at=_now_utc()))
            db.commit()

    def list_onchain_cursors(self, *, limit: int = 200) -> list[dict]:
        with self._session() as db:
            q = select(OnchainCursorDB).order_by(OnchainCursorDB.updated_at.desc()).limit(max(1, int(limit)))
            rows = list(db.execute(q).scalars().all())
        return [{"key": r.key, "last_block": int(r.last_block), "updated_at": _dt_to_iso(r.updated_at) or utc_now_iso()} for r in rows]

    # ---- Jobs ----
    def _job_to_dict(self, j: JobDB) -> dict:
        return {
            "id": j.id,
            "title": j.title,
            "prompt": j.prompt,
            "bounty_usdc": float(j.bounty_usdc),
            "tags": list(j.tags or []),
            "status": j.status,
            "sponsor_address": j.sponsor_address,
            "created_at": _dt_to_iso(j.created_at),
            "winner_submission_id": j.winner_submission_id,
            "closed_at": _dt_to_iso(j.closed_at),
            "close_tx_hash": j.close_tx_hash,
            "close_chain_id": int(j.close_chain_id) if j.close_chain_id is not None else None,
            "close_contract_address": j.close_contract_address,
            "close_block_number": int(j.close_block_number) if j.close_block_number is not None else None,
            "close_log_index": int(j.close_log_index) if j.close_log_index is not None else None,
            "final_vote_starts_at": _dt_to_iso(_ensure_utc(j.final_vote_starts_at)),
            "final_vote_ends_at": _dt_to_iso(_ensure_utc(j.final_vote_ends_at)),
            "featured_until": _dt_to_iso(_ensure_utc(j.featured_until)),
            "featured_score": int(j.featured_score or 0),
        }

    def create_job(self, job: dict) -> dict:
        job_id = str(uuid.uuid4())
        created_at = _parse_iso(str(job.get("created_at") or "")) or _now_utc()
        final_vote_starts_at = _parse_iso(str(job.get("final_vote_starts_at") or "")) or None
        final_vote_ends_at = _parse_iso(str(job.get("final_vote_ends_at") or "")) or None
        row = JobDB(
            id=job_id,
            title=str(job.get("title") or ""),
            prompt=str(job.get("prompt") or ""),
            bounty_usdc=float(job.get("bounty_usdc") or 0.0),
            tags=list(job.get("tags") or []),
            status=str(job.get("status") or "open"),
            sponsor_address=_lower_addr(str(job.get("sponsor_address") or "")) or None,
            created_at=created_at,
            final_vote_starts_at=final_vote_starts_at,
            final_vote_ends_at=final_vote_ends_at,
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return self._job_to_dict(row)

    # ---- Community posts ----
    def _post_to_dict(self, p: PostDB) -> dict:
        return {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "author_address": p.author_address,
            "tags": list(p.tags or []),
            "created_at": _dt_to_iso(p.created_at),
            "deleted_at": _dt_to_iso(p.deleted_at),
            "deleted_by": p.deleted_by,
        }

    def create_post(self, post: dict) -> dict:
        post_id = str(uuid.uuid4())
        created_at = _parse_iso(str(post.get("created_at") or "")) or _now_utc()
        row = PostDB(
            id=post_id,
            title=str(post.get("title") or ""),
            content=str(post.get("content") or ""),
            author_address=_lower_addr(str(post.get("author_address") or "")),
            tags=list(post.get("tags") or []),
            created_at=created_at,
            deleted_at=None,
            deleted_by=None,
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return self._post_to_dict(row)

    def list_posts(self, *, tag: str | None = None, limit: int = 50) -> list[dict]:
        lim = max(1, int(limit))
        with self._session() as db:
            q = (
                select(PostDB)
                .where(PostDB.deleted_at.is_(None))
                .order_by(PostDB.created_at.desc())
                .limit(lim * 5)  # small cushion for python-side tag filtering
            )
            rows = list(db.execute(q).scalars().all())
        posts = [self._post_to_dict(r) for r in rows]
        if tag:
            t = tag.strip().lower()
            posts = [p for p in posts if any(str(x).lower() == t for x in (p.get("tags") or []))]
        return posts[:lim]

    def get_post(self, post_id: str) -> dict | None:
        pid = str(post_id)
        with self._session() as db:
            row = db.get(PostDB, pid)
            if not row or row.deleted_at is not None:
                return None
            return self._post_to_dict(row)

    # ---- Semantic search (optional) ----
    def _semantic_doc_to_dict(self, d: SemanticDocDB) -> dict:
        return {
            "id": d.id,
            "doc_type": d.doc_type,
            "doc_id": d.doc_id,
            "text": d.text,
            "embedding": list(d.embedding or []),
            "updated_at": _dt_to_iso(d.updated_at),
        }

    def upsert_semantic_doc(self, *, doc_type: str, doc_id: str, text: str, embedding: list[float]) -> dict:
        dt = str(doc_type)
        did = str(doc_id)
        now = _now_utc()
        with self._session() as db:
            existing = db.execute(
                select(SemanticDocDB).where(SemanticDocDB.doc_type == dt, SemanticDocDB.doc_id == did)
            ).scalar_one_or_none()
            if existing:
                existing.text = str(text)
                existing.embedding = list(embedding or [])
                existing.updated_at = now
                db.commit()
                db.refresh(existing)
                return self._semantic_doc_to_dict(existing)

            row = SemanticDocDB(
                id=str(uuid.uuid4()),
                doc_type=dt,
                doc_id=did,
                text=str(text),
                embedding=list(embedding or []),
                updated_at=now,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._semantic_doc_to_dict(row)

    def list_semantic_docs(self, *, doc_type: str | None = None, limit: int = 2000) -> list[dict]:
        lim = max(1, int(limit))
        with self._session() as db:
            q = select(SemanticDocDB).order_by(SemanticDocDB.updated_at.desc())
            if doc_type:
                q = q.where(SemanticDocDB.doc_type == str(doc_type))
            q = q.limit(lim)
            rows = list(db.execute(q).scalars().all())
        return [self._semantic_doc_to_dict(r) for r in rows]

    def list_jobs(self, *, status: str = "open", tag: str | None = None) -> list[dict]:
        with self._session() as db:
            # featured first, then recency
            q = select(JobDB).order_by(JobDB.featured_until.desc().nullslast(), JobDB.featured_score.desc(), JobDB.created_at.desc())
            if status != "all":
                q = q.where(JobDB.status == "open")
            rows = list(db.execute(q).scalars().all())
        jobs = [self._job_to_dict(r) for r in rows]
        if tag:
            t = tag.strip().lower()
            jobs = [j for j in jobs if any(str(x).lower() == t for x in (j.get("tags") or []))]
        return jobs

    # ---- AGR credits (offchain) ----
    def agr_balance(self, address: str) -> dict:
        addr = _lower_addr(address)
        with self._session() as db:
            rows = list(db.execute(select(AgrLedgerDB).where(AgrLedgerDB.address == addr)).scalars().all())
        earned = sum(int(r.delta) for r in rows if int(r.delta) > 0)
        spent = -sum(int(r.delta) for r in rows if int(r.delta) < 0)
        return {"address": addr, "earned": int(earned), "spent": int(spent), "balance": int(earned - spent)}

    def agr_credit(self, *, address: str, amount: int, reason: str, job_id: str | None = None) -> dict:
        addr = _lower_addr(address)
        amt = int(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        row = AgrLedgerDB(
            id=str(uuid.uuid4()),
            address=addr,
            delta=amt,
            reason=str(reason),
            job_id=str(job_id) if job_id else None,
            created_at=_now_utc(),
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"id": row.id, "address": row.address, "delta": int(row.delta), "reason": row.reason, "job_id": row.job_id, "created_at": _dt_to_iso(row.created_at)}

    def agr_debit(self, *, address: str, amount: int, reason: str, job_id: str | None = None) -> dict:
        addr = _lower_addr(address)
        amt = int(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        bal = int(self.agr_balance(addr)["balance"])
        if bal < amt:
            raise ValueError("insufficient AGR balance")
        row = AgrLedgerDB(
            id=str(uuid.uuid4()),
            address=addr,
            delta=-amt,
            reason=str(reason),
            job_id=str(job_id) if job_id else None,
            created_at=_now_utc(),
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"id": row.id, "address": row.address, "delta": int(row.delta), "reason": row.reason, "job_id": row.job_id, "created_at": _dt_to_iso(row.created_at)}

    def boost_job(self, *, job_id: str, address: str, amount_agr: int, duration_seconds: int) -> dict:
        addr = _lower_addr(address)
        amt = int(amount_agr)
        dur = int(duration_seconds)
        if amt <= 0 or dur <= 0:
            raise ValueError("amount_agr and duration_seconds must be > 0")

        with self._session() as db:
            job = db.get(JobDB, job_id)
            if not job:
                raise KeyError("Job not found")

            # ensure balance before writing
            bal = self.agr_balance(addr)["balance"]
            if int(bal) < amt:
                raise ValueError("insufficient AGR balance")

            # debit
            db.add(
                AgrLedgerDB(
                    id=str(uuid.uuid4()),
                    address=addr,
                    delta=-amt,
                    reason="job_boost",
                    job_id=job_id,
                    created_at=_now_utc(),
                )
            )

            now = _now_utc()
            base = job.featured_until if job.featured_until and job.featured_until > now else now
            featured_until = base + timedelta(seconds=dur)
            job.featured_until = featured_until
            job.featured_score = int(job.featured_score or 0) + amt

            boost = JobBoostDB(
                id=str(uuid.uuid4()),
                job_id=job_id,
                address=addr,
                amount_agr=amt,
                duration_seconds=dur,
                featured_until=featured_until,
                created_at=_now_utc(),
            )
            db.add(boost)
            db.commit()
            db.refresh(job)
            return {"job_id": job_id, "featured_until": _dt_to_iso(job.featured_until), "featured_score": int(job.featured_score or 0)}

    def list_agr_ledger(self, *, address: str, limit: int = 50) -> list[dict]:
        addr = _lower_addr(address)
        lim = max(1, int(limit))
        with self._session() as db:
            q = (
                select(AgrLedgerDB)
                .where(AgrLedgerDB.address == addr)
                .order_by(AgrLedgerDB.created_at.desc())
                .limit(lim)
            )
            rows = list(db.execute(q).scalars().all())
        return [
            {"id": r.id, "address": r.address, "delta": int(r.delta), "reason": r.reason, "job_id": r.job_id, "created_at": _dt_to_iso(r.created_at)}
            for r in rows
        ]

    def get_job(self, job_id: str) -> dict | None:
        with self._session() as db:
            row = db.get(JobDB, job_id)
            return self._job_to_dict(row) if row else None

    def close_job(
        self,
        job_id: str,
        winner_submission_id: str,
        closed_at_iso: str,
        *,
        close_tx_hash: str | None = None,
        close_chain_id: int | None = None,
        close_contract_address: str | None = None,
        close_block_number: int | None = None,
        close_log_index: int | None = None,
    ) -> dict:
        closed_at = _parse_iso(closed_at_iso) or _now_utc()
        with self._session() as db:
            row = db.get(JobDB, job_id)
            if not row:
                raise KeyError("Job not found")
            row.status = "closed"
            row.winner_submission_id = winner_submission_id
            row.closed_at = closed_at
            row.close_tx_hash = close_tx_hash
            row.close_chain_id = int(close_chain_id) if close_chain_id is not None else None
            row.close_contract_address = close_contract_address
            row.close_block_number = int(close_block_number) if close_block_number is not None else None
            row.close_log_index = int(close_log_index) if close_log_index is not None else None
            db.commit()
            db.refresh(row)
            return self._job_to_dict(row)

    # ---- Submissions ----
    def _submission_to_dict(self, s: SubmissionDB) -> dict:
        return {
            "id": s.id,
            "job_id": s.job_id,
            "agent_address": s.agent_address,
            "content": s.content,
            "evidence": list(s.evidence or []),
            "created_at": _dt_to_iso(s.created_at),
        }

    def create_submission(self, submission: dict) -> dict:
        sub_id = str(uuid.uuid4())
        created_at = _parse_iso(str(submission.get("created_at") or "")) or _now_utc()
        row = SubmissionDB(
            id=sub_id,
            job_id=str(submission.get("job_id") or ""),
            agent_address=_lower_addr(str(submission.get("agent_address") or "")),
            content=str(submission.get("content") or ""),
            evidence=list(submission.get("evidence") or []),
            created_at=created_at,
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return self._submission_to_dict(row)

    def get_submission(self, submission_id: str) -> dict | None:
        sid = str(submission_id)
        with self._session() as db:
            row = db.get(SubmissionDB, sid)
            if not row:
                return None
            return self._submission_to_dict(row)

    def list_submissions_for_job(self, job_id: str) -> list[dict]:
        with self._session() as db:
            q = select(SubmissionDB).where(SubmissionDB.job_id == job_id).order_by(SubmissionDB.created_at.asc())
            rows = list(db.execute(q).scalars().all())
        return [self._submission_to_dict(r) for r in rows]

    # ---- Votes ----
    def _vote_to_dict(self, v: VoteDB) -> dict:
        return {
            "id": v.id,
            "job_id": v.job_id,
            "submission_id": v.submission_id,
            "voter_address": v.voter_address,
            "weight": float(v.weight),
            "review": dict(v.review) if v.review else None,
            "created_at": _dt_to_iso(v.created_at),
        }

    def _final_vote_to_dict(self, v: FinalVoteDB) -> dict:
        return {
            "id": v.id,
            "job_id": v.job_id,
            "submission_id": v.submission_id,
            "voter_address": v.voter_address,
            "created_at": _dt_to_iso(v.created_at),
        }

    def upsert_vote(self, *, job_id: str, voter_address: str, vote: dict) -> dict:
        voter = _lower_addr(voter_address)
        created_at = _parse_iso(str(vote.get("created_at") or "")) or _now_utc()
        submission_id = str(vote.get("submission_id") or "")
        weight = float(vote.get("weight") or 1.0)
        review = vote.get("review")
        review_obj = dict(review) if isinstance(review, dict) else None

        with self._session() as db:
            existing = db.execute(
                select(VoteDB).where(VoteDB.job_id == job_id, VoteDB.voter_address == voter)
            ).scalar_one_or_none()
            if existing:
                existing.submission_id = submission_id
                existing.weight = weight
                existing.review = review_obj
                existing.created_at = created_at
                db.commit()
                db.refresh(existing)
                return self._vote_to_dict(existing)

            row = VoteDB(
                id=str(uuid.uuid4()),
                job_id=job_id,
                submission_id=submission_id,
                voter_address=voter,
                weight=weight,
                review=review_obj,
                created_at=created_at,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._vote_to_dict(row)

    # ---- Discussion (comments) ----
    def _comment_to_dict(self, c: CommentDB) -> dict:
        return {
            "id": c.id,
            "target_type": c.target_type,
            "target_id": c.target_id,
            "parent_id": c.parent_id,
            "author_address": c.author_address,
            "content": c.content,
            "created_at": _dt_to_iso(c.created_at),
            "deleted_at": _dt_to_iso(c.deleted_at),
            "deleted_by": c.deleted_by,
        }

    def create_comment(self, *, comment: dict) -> dict:
        cid = str(uuid.uuid4())
        created_at = _parse_iso(str(comment.get("created_at") or "")) or _now_utc()
        row = CommentDB(
            id=cid,
            target_type=str(comment.get("target_type") or ""),
            target_id=str(comment.get("target_id") or ""),
            parent_id=str(comment.get("parent_id") or "") or None,
            author_address=_lower_addr(str(comment.get("author_address") or "")),
            content=str(comment.get("content") or ""),
            created_at=created_at,
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return self._comment_to_dict(row)

    def get_comment(self, *, comment_id: str) -> dict | None:
        cid = str(comment_id)
        with self._session() as db:
            row = db.get(CommentDB, cid)
            if not row:
                return None
            return self._comment_to_dict(row)

    def list_comments(self, *, target_type: str, target_id: str, limit: int = 200) -> list[dict]:
        t = str(target_type)
        tid = str(target_id)
        lim = int(limit)
        with self._session() as db:
            q = (
                select(CommentDB)
                .where(CommentDB.target_type == t, CommentDB.target_id == tid)
                .order_by(CommentDB.created_at.asc())
                .limit(lim)
            )
            rows = list(db.execute(q).scalars().all())
        return [self._comment_to_dict(r) for r in rows]

    def soft_delete_comment(self, *, comment_id: str, deleted_by: str) -> dict:
        cid = str(comment_id)
        deleter = _lower_addr(deleted_by)
        now = _now_utc()
        with self._session() as db:
            row = db.get(CommentDB, cid)
            if not row:
                raise KeyError("Comment not found")
            if row.deleted_at is None:
                row.deleted_at = now
                row.deleted_by = deleter
                db.commit()
                db.refresh(row)
            return self._comment_to_dict(row)

    # ---- Engagement (reactions/views) ----
    def upsert_reaction(self, *, actor_address: str, target_type: str, target_id: str, kind: str) -> bool:
        actor = _lower_addr(actor_address)
        t = str(target_type)
        tid = str(target_id)
        k = str(kind)
        row = ReactionDB(
            id=str(uuid.uuid4()),
            target_type=t,
            target_id=tid,
            kind=k,
            actor_address=actor,
            created_at=_now_utc(),
        )
        with self._session() as db:
            try:
                db.add(row)
                db.commit()
                return True
            except Exception:
                db.rollback()
                # Likely unique constraint violation -> already exists.
                return False

    def delete_reaction(self, *, actor_address: str, target_type: str, target_id: str, kind: str) -> bool:
        actor = _lower_addr(actor_address)
        t = str(target_type)
        tid = str(target_id)
        k = str(kind)
        with self._session() as db:
            q = delete(ReactionDB).where(
                ReactionDB.actor_address == actor,
                ReactionDB.target_type == t,
                ReactionDB.target_id == tid,
                ReactionDB.kind == k,
            )
            res = db.execute(q)
            db.commit()
            return bool(getattr(res, "rowcount", 0) or 0)

    def record_view(self, *, viewer_address: str, target_type: str, target_id: str) -> bool:
        viewer = _lower_addr(viewer_address)
        t = str(target_type)
        tid = str(target_id)
        now = _now_utc()
        window_start = now.replace(minute=0, second=0, microsecond=0)
        row = ViewEventDB(
            id=str(uuid.uuid4()),
            target_type=t,
            target_id=tid,
            viewer_address=viewer,
            window_start=window_start,
            created_at=now,
        )
        with self._session() as db:
            try:
                db.add(row)
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

    def get_engagement_stats(self, *, target_type: str, target_id: str) -> dict[str, int]:
        tid = str(target_id)
        return (self.get_engagement_stats_batch(target_type=str(target_type), target_ids=[tid]) or {}).get(tid, {})

    def get_engagement_stats_batch(self, *, target_type: str, target_ids: list[str]) -> dict[str, dict[str, int]]:
        t = str(target_type)
        ids = [str(x) for x in (target_ids or []) if str(x)]
        if not ids:
            return {}

        out: dict[str, dict[str, int]] = {tid: {"upvotes": 0, "bookmarks": 0, "views": 0, "comments": 0} for tid in ids}

        with self._session() as db:
            # Comments (exclude soft-deleted)
            cq = (
                select(CommentDB.target_id, func.count())
                .where(CommentDB.target_type == t, CommentDB.target_id.in_(ids), CommentDB.deleted_at.is_(None))
                .group_by(CommentDB.target_id)
            )
            for target_id, cnt in db.execute(cq).all():
                tid = str(target_id)
                if tid in out:
                    out[tid]["comments"] = int(cnt or 0)

            # Reactions
            rq = (
                select(ReactionDB.target_id, ReactionDB.kind, func.count())
                .where(ReactionDB.target_type == t, ReactionDB.target_id.in_(ids))
                .group_by(ReactionDB.target_id, ReactionDB.kind)
            )
            for target_id, kind, cnt in db.execute(rq).all():
                tid = str(target_id)
                if tid not in out:
                    continue
                k = str(kind or "")
                if k == "upvote":
                    out[tid]["upvotes"] = int(cnt or 0)
                elif k == "bookmark":
                    out[tid]["bookmarks"] = int(cnt or 0)

            # Views (view_events are already deduped per viewer per hour)
            vq = (
                select(ViewEventDB.target_id, func.count())
                .where(ViewEventDB.target_type == t, ViewEventDB.target_id.in_(ids))
                .group_by(ViewEventDB.target_id)
            )
            for target_id, cnt in db.execute(vq).all():
                tid = str(target_id)
                if tid in out:
                    out[tid]["views"] = int(cnt or 0)

        return out

    # ---- Notifications ----
    def _notification_to_dict(self, n: NotificationDB) -> dict:
        return {
            "id": n.id,
            "recipient_address": n.recipient_address,
            "actor_address": n.actor_address,
            "type": n.type,
            "target_type": n.target_type,
            "target_id": n.target_id,
            "payload": dict(n.payload or {}),
            "created_at": _dt_to_iso(n.created_at),
            "read_at": _dt_to_iso(n.read_at),
        }

    def create_notification(self, *, notification: dict) -> dict:
        nid = str(uuid.uuid4())
        row = NotificationDB(
            id=nid,
            recipient_address=_lower_addr(str(notification.get("recipient_address") or "")),
            actor_address=_lower_addr(str(notification.get("actor_address") or "")) if notification.get("actor_address") else None,
            type=str(notification.get("type") or ""),
            target_type=str(notification.get("target_type") or ""),
            target_id=str(notification.get("target_id") or ""),
            payload=dict(notification.get("payload") or {}),
            created_at=_parse_iso(str(notification.get("created_at") or "")) or _now_utc(),
            read_at=_parse_iso(str(notification.get("read_at") or "")) if notification.get("read_at") else None,
        )
        with self._session() as db:
            db.add(row)
            db.commit()
            db.refresh(row)
        return self._notification_to_dict(row)

    def list_notifications(self, *, recipient_address: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
        addr = _lower_addr(recipient_address)
        lim = max(1, int(limit))
        with self._session() as db:
            q = select(NotificationDB).where(NotificationDB.recipient_address == addr)
            if unread_only:
                q = q.where(NotificationDB.read_at.is_(None))
            q = q.order_by(NotificationDB.created_at.desc()).limit(lim)
            rows = list(db.execute(q).scalars().all())
        return [self._notification_to_dict(r) for r in rows]

    def mark_notification_read(self, *, recipient_address: str, notification_id: str) -> dict | None:
        addr = _lower_addr(recipient_address)
        nid = str(notification_id)
        now = _now_utc()
        with self._session() as db:
            row = db.get(NotificationDB, nid)
            if not row:
                return None
            if _lower_addr(str(row.recipient_address or "")) != addr:
                return None
            if row.read_at is None:
                row.read_at = now
                db.commit()
                db.refresh(row)
            return self._notification_to_dict(row)

    def list_votes_for_job(self, job_id: str) -> list[dict]:
        with self._session() as db:
            q = select(VoteDB).where(VoteDB.job_id == job_id).order_by(VoteDB.created_at.asc())
            rows = list(db.execute(q).scalars().all())
        return [self._vote_to_dict(r) for r in rows]

    def tally_votes_for_job(self, job_id: str) -> dict[str, dict]:
        tallies: dict[str, dict] = {}
        for v in self.list_votes_for_job(job_id):
            sid = v.get("submission_id")
            if not sid:
                continue
            if sid not in tallies:
                tallies[sid] = {"submission_id": sid, "weighted_votes": 0.0, "voters": 0}
            tallies[sid]["weighted_votes"] += float(v.get("weight", 1.0))
            tallies[sid]["voters"] += 1
        return tallies

    # ---- Final decision votes ----
    def upsert_final_vote(self, *, job_id: str, voter_address: str, submission_id: str) -> dict:
        addr = _lower_addr(voter_address)
        with self._session() as db:
            existing = db.execute(
                select(FinalVoteDB).where(FinalVoteDB.job_id == job_id, FinalVoteDB.voter_address == addr)
            ).scalar_one_or_none()
            if existing:
                existing.submission_id = submission_id
                existing.created_at = _now_utc()
                db.commit()
                db.refresh(existing)
                return self._final_vote_to_dict(existing)

            row = FinalVoteDB(
                id=str(uuid.uuid4()),
                job_id=job_id,
                submission_id=submission_id,
                voter_address=addr,
                created_at=_now_utc(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._final_vote_to_dict(row)

    def list_final_votes_for_job(self, job_id: str) -> list[dict]:
        with self._session() as db:
            q = select(FinalVoteDB).where(FinalVoteDB.job_id == job_id).order_by(FinalVoteDB.created_at.asc())
            rows = list(db.execute(q).scalars().all())
        return [self._final_vote_to_dict(r) for r in rows]

    def tally_final_votes_for_job(self, job_id: str) -> dict[str, dict]:
        votes = self.list_final_votes_for_job(job_id)
        tallies: dict[str, dict] = {}
        for v in votes:
            sid = str(v.get("submission_id") or "")
            if not sid:
                continue
            t = tallies.get(sid) or {"submission_id": sid, "votes": 0, "voters": 0}
            t["votes"] = int(t.get("votes", 0)) + 1
            t["voters"] = int(t.get("voters", 0)) + 1
            tallies[sid] = t
        return tallies

    # ---- Reputation ----
    def ensure_agent_rep(self, address: str) -> dict:
        addr = _lower_addr(address)
        with self._session() as db:
            row = db.get(AgentReputationDB, addr)
            if not row:
                row = AgentReputationDB(
                    address=addr,
                    score=0.0,
                    level=1,
                    wins=0,
                    losses=0,
                    badges=[],
                    last_updated_at=_now_utc(),
                )
                db.add(row)
                db.commit()
                db.refresh(row)
            return {
                "address": row.address,
                "score": float(row.score),
                "level": int(row.level),
                "wins": int(row.wins),
                "losses": int(row.losses),
                "badges": list(row.badges or []),
                "last_updated_at": _dt_to_iso(row.last_updated_at) or "",
            }

    def set_rep_score(self, address: str, score: float) -> dict:
        addr = _lower_addr(address)
        rep = self.ensure_agent_rep(addr)
        new_score = float(score)
        new_level = max(1, int(new_score // 100) + 1)
        updated_at = _now_utc()
        with self._session() as db:
            row = db.get(AgentReputationDB, addr)
            if not row:
                return self.ensure_agent_rep(addr)
            row.score = new_score
            row.level = new_level
            row.last_updated_at = updated_at
            db.commit()
        rep["score"] = new_score
        rep["level"] = new_level
        rep["last_updated_at"] = _dt_to_iso(updated_at) or rep.get("last_updated_at", "")
        return rep

    def bump_rep_for_submission(self, address: str, delta: float) -> dict:
        addr = _lower_addr(address)
        rep = self.ensure_agent_rep(addr)
        new_score = float(rep.get("score", 0.0)) + float(delta)
        return self.set_rep_score(addr, new_score)

    def get_rep(self, address: str) -> dict:
        return self.ensure_agent_rep(address)

    def leaderboard(self, limit: int = 50) -> list[dict]:
        with self._session() as db:
            q = select(AgentReputationDB).order_by(AgentReputationDB.score.desc()).limit(int(limit))
            rows = list(db.execute(q).scalars().all())
        return [{"address": r.address, "score": float(r.score), "level": int(r.level)} for r in rows]

    # ---- Profile ----
    def get_profile(self, address: str) -> dict:
        addr = _lower_addr(address)
        with self._session() as db:
            row = db.get(AgentProfileDB, addr)
            if not row:
                base = {
                    "address": addr,
                    "nickname": None,
                    "avatar_url": None,
                    "avatar_mode": "manual",
                    "participant_type": "unknown",
                    "updated_at": utc_now_iso(),
                }
            else:
                base = {
                    "address": row.address,
                    "nickname": row.nickname,
                    "avatar_url": row.avatar_url,
                    "avatar_mode": row.avatar_mode,
                    "participant_type": getattr(row, "participant_type", None) or "unknown",
                    "updated_at": _dt_to_iso(row.updated_at) or utc_now_iso(),
                }
        # Add optional deterministic seed for donor avatars.
        if base.get("avatar_mode") == "donor":
            t = self.get_donor_total(addr)
            first_id = (t or {}).get("first_event_id")
            if first_id:
                base["avatar_seed"] = f"{addr}:{first_id}"
            else:
                base["avatar_seed"] = addr
        return base

    # ---- Donations ----
    def record_donation_event(self, *, event: dict) -> dict:
        ev_id = str(event.get("id") or "")
        if not ev_id:
            raise ValueError("donation event missing id")
        donor = _lower_addr(str(event.get("donor_address") or ""))
        asset = _lower_addr(str(event.get("asset_address") or ""))
        amount_raw = int(event.get("amount_raw") or 0)
        amount_usd = float(event.get("amount_usd")) if event.get("amount_usd") is not None else None
        purpose_id = int(event.get("purpose_id")) if event.get("purpose_id") is not None else None
        memo_hash = str(event.get("memo_hash")) if event.get("memo_hash") else None
        tx_hash = str(event.get("tx_hash") or "").lower()
        chain_id = int(event.get("chain_id") or 0)
        contract = _lower_addr(str(event.get("contract_address") or ""))
        block_number = int(event.get("block_number") or 0)
        log_index = int(event.get("log_index") or 0)
        created_at = _parse_iso(str(event.get("created_at") or "")) or _now_utc()

        with self._session() as db:
            existing = db.get(DonationEventDB, ev_id)
            if existing:
                return {
                    "id": existing.id,
                    "donor_address": existing.donor_address,
                    "asset_address": existing.asset_address,
                    "amount_raw": int(existing.amount_raw),
                    "amount_usd": float(existing.amount_usd) if existing.amount_usd is not None else None,
                    "purpose_id": int(existing.purpose_id) if existing.purpose_id is not None else None,
                    "memo_hash": existing.memo_hash,
                    "tx_hash": existing.tx_hash,
                    "chain_id": int(existing.chain_id),
                    "contract_address": existing.contract_address,
                    "block_number": int(existing.block_number),
                    "log_index": int(existing.log_index),
                    "created_at": _dt_to_iso(existing.created_at),
                }

            row = DonationEventDB(
                id=ev_id,
                donor_address=donor,
                asset_address=asset,
                amount_raw=amount_raw,
                amount_usd=amount_usd,
                purpose_id=purpose_id,
                memo_hash=memo_hash,
                tx_hash=tx_hash,
                chain_id=chain_id,
                contract_address=contract,
                block_number=block_number,
                log_index=log_index,
                created_at=created_at,
            )
            db.add(row)

            # Update donor totals (best-effort; only when we have amount_usd)
            totals = db.get(DonorTotalDB, donor)
            if not totals:
                totals = DonorTotalDB(donor_address=donor, total_usd=0.0, first_event_id=ev_id, updated_at=_now_utc())
                db.add(totals)
            if not totals.first_event_id:
                totals.first_event_id = ev_id
            if amount_usd is not None:
                totals.total_usd = float(totals.total_usd or 0.0) + float(amount_usd)
            totals.updated_at = _now_utc()

            # Auto-enable donor avatar if eligible.
            try:
                if float(totals.total_usd or 0.0) >= float(getattr(settings, "DONOR_THRESHOLD_USD", 10.0)):
                    prof = db.get(AgentProfileDB, donor)
                    if prof:
                        prof.avatar_mode = "donor"
                        prof.avatar_url = None
                        prof.updated_at = _now_utc()
                    else:
                        db.add(AgentProfileDB(address=donor, nickname=None, avatar_url=None, avatar_mode="donor", updated_at=_now_utc()))
            except Exception:
                pass

            db.commit()
            db.refresh(row)
            return {
                "id": row.id,
                "donor_address": row.donor_address,
                "asset_address": row.asset_address,
                "amount_raw": int(row.amount_raw),
                "amount_usd": float(row.amount_usd) if row.amount_usd is not None else None,
                "purpose_id": int(row.purpose_id) if row.purpose_id is not None else None,
                "memo_hash": row.memo_hash,
                "tx_hash": row.tx_hash,
                "chain_id": int(row.chain_id),
                "contract_address": row.contract_address,
                "block_number": int(row.block_number),
                "log_index": int(row.log_index),
                "created_at": _dt_to_iso(row.created_at),
            }

    def get_donor_total(self, address: str) -> dict | None:
        addr = _lower_addr(address)
        with self._session() as db:
            row = db.get(DonorTotalDB, addr)
            if not row:
                return None
            return {
                "donor_address": row.donor_address,
                "total_usd": float(row.total_usd or 0.0),
                "first_event_id": row.first_event_id,
                "updated_at": _dt_to_iso(row.updated_at),
            }

    def list_donation_events(self, *, limit: int = 50) -> list[dict]:
        with self._session() as db:
            q = select(DonationEventDB).order_by(DonationEventDB.created_at.desc()).limit(max(1, int(limit)))
            rows = list(db.execute(q).scalars().all())
        out = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "donor_address": r.donor_address,
                    "asset_address": r.asset_address,
                    "amount_raw": int(r.amount_raw),
                    "amount_usd": float(r.amount_usd) if r.amount_usd is not None else None,
                    "purpose_id": int(r.purpose_id) if r.purpose_id is not None else None,
                    "memo_hash": r.memo_hash,
                    "tx_hash": r.tx_hash,
                    "chain_id": int(r.chain_id),
                    "contract_address": r.contract_address,
                    "block_number": int(r.block_number),
                    "log_index": int(r.log_index),
                    "created_at": _dt_to_iso(r.created_at) or utc_now_iso(),
                }
            )
        return out

    # ---- Anchoring ----
    def upsert_anchor_batch(self, *, job_id: str, anchor_root: str, anchor_uri: str, schema_version: int, salt: str) -> dict:
        jid = str(job_id)
        with self._session() as db:
            existing = db.execute(select(AnchorBatchDB).where(AnchorBatchDB.job_id == jid)).scalar_one_or_none()
            if existing:
                return self.get_anchor_batch(jid) or {}
            row = AnchorBatchDB(
                id=str(uuid.uuid4()),
                job_id=jid,
                schema_version=int(schema_version),
                salt=str(salt),
                anchor_root=str(anchor_root),
                anchor_uri=str(anchor_uri),
                anchor_tx_hash=None,
                anchor_chain_id=None,
                anchor_contract_address=None,
                anchor_block_number=None,
                anchor_log_index=None,
                created_at=_now_utc(),
            )
            db.add(row)
            db.commit()
        return self.get_anchor_batch(jid) or {}

    def get_anchor_batch(self, job_id: str) -> dict | None:
        jid = str(job_id)
        with self._session() as db:
            row = db.execute(select(AnchorBatchDB).where(AnchorBatchDB.job_id == jid)).scalar_one_or_none()
            if not row:
                return None
            return {
                "id": row.id,
                "job_id": row.job_id,
                "schema_version": int(row.schema_version),
                "salt": row.salt,
                "anchor_root": row.anchor_root,
                "anchor_uri": row.anchor_uri,
                "anchor_tx_hash": row.anchor_tx_hash,
                "anchor_chain_id": int(row.anchor_chain_id) if row.anchor_chain_id is not None else None,
                "anchor_contract_address": row.anchor_contract_address,
                "anchor_block_number": int(row.anchor_block_number) if row.anchor_block_number is not None else None,
                "anchor_log_index": int(row.anchor_log_index) if row.anchor_log_index is not None else None,
                "created_at": _dt_to_iso(row.created_at),
            }

    def list_anchor_batches(self, *, limit: int = 50) -> list[dict]:
        with self._session() as db:
            q = select(AnchorBatchDB).order_by(AnchorBatchDB.created_at.desc()).limit(max(1, int(limit)))
            rows = list(db.execute(q).scalars().all())
        out = []
        for row in rows:
            out.append(
                {
                    "id": row.id,
                    "job_id": row.job_id,
                    "schema_version": int(row.schema_version),
                    "salt": row.salt,
                    "anchor_root": row.anchor_root,
                    "anchor_uri": row.anchor_uri,
                    "anchor_tx_hash": row.anchor_tx_hash,
                    "anchor_chain_id": int(row.anchor_chain_id) if row.anchor_chain_id is not None else None,
                    "anchor_contract_address": row.anchor_contract_address,
                    "anchor_block_number": int(row.anchor_block_number) if row.anchor_block_number is not None else None,
                    "anchor_log_index": int(row.anchor_log_index) if row.anchor_log_index is not None else None,
                    "created_at": _dt_to_iso(row.created_at) or utc_now_iso(),
                }
            )
        return out

    def set_anchor_receipt(
        self,
        *,
        job_id: str,
        anchor_tx_hash: str,
        anchor_chain_id: int,
        anchor_contract_address: str,
        anchor_block_number: int,
        anchor_log_index: int,
    ) -> dict:
        jid = str(job_id)
        with self._session() as db:
            row = db.execute(select(AnchorBatchDB).where(AnchorBatchDB.job_id == jid)).scalar_one_or_none()
            if not row:
                raise KeyError("Anchor batch not found for job")
            row.anchor_tx_hash = str(anchor_tx_hash).lower()
            row.anchor_chain_id = int(anchor_chain_id)
            row.anchor_contract_address = _lower_addr(str(anchor_contract_address))
            row.anchor_block_number = int(anchor_block_number)
            row.anchor_log_index = int(anchor_log_index)
            db.commit()
        return self.get_anchor_batch(jid) or {}

    def upsert_profile(
        self, *, address: str, nickname: str | None, avatar_url: str | None, avatar_mode: str, participant_type: str
    ) -> dict:
        addr = _lower_addr(address)
        now = _now_utc()
        with self._session() as db:
            row = db.get(AgentProfileDB, addr)
            if row:
                row.nickname = nickname
                row.avatar_url = avatar_url
                row.avatar_mode = avatar_mode
                row.participant_type = participant_type or "unknown"
                row.updated_at = now
            else:
                db.add(
                    AgentProfileDB(
                        address=addr,
                        nickname=nickname,
                        avatar_url=avatar_url,
                        avatar_mode=avatar_mode,
                        participant_type=participant_type or "unknown",
                        updated_at=now,
                    )
                )
            db.commit()
        return self.get_profile(addr)

    def get_profiles(self, *, addresses: list[str]) -> list[dict]:
        addrs = [_lower_addr(str(a)) for a in (addresses or []) if str(a).strip()]
        if not addrs:
            return []
        with self._session() as db:
            q = select(AgentProfileDB).where(AgentProfileDB.address.in_(addrs))
            rows = list(db.execute(q).scalars().all())
        found = {r.address: r for r in rows}
        out: list[dict] = []
        for a in addrs:
            r = found.get(a)
            if not r:
                out.append(self.get_profile(a))
            else:
                out.append(self.get_profile(r.address))
        return out

    # ---- Admin ----
    def admin_metrics(self) -> dict:
        with self._session() as db:
            users_rep = db.execute(select(func.count()).select_from(AgentReputationDB)).scalar_one()
            users_sessions = db.execute(select(func.count(func.distinct(AuthSessionDB.address)))).scalar_one()
            jobs_total = db.execute(select(func.count()).select_from(JobDB)).scalar_one()
            jobs_open = db.execute(select(func.count()).select_from(JobDB).where(JobDB.status == "open")).scalar_one()
            submissions_total = db.execute(select(func.count()).select_from(SubmissionDB)).scalar_one()
            comments_total = db.execute(select(func.count()).select_from(CommentDB)).scalar_one()
            votes_total = db.execute(select(func.count()).select_from(VoteDB)).scalar_one()
            final_votes_total = db.execute(select(func.count()).select_from(FinalVoteDB)).scalar_one()
            active_sessions = db.execute(select(func.count()).select_from(AuthSessionDB)).scalar_one()

        return {
            "users": int(max(int(users_rep or 0), int(users_sessions or 0))),
            "jobs_total": int(jobs_total or 0),
            "jobs_open": int(jobs_open or 0),
            "submissions_total": int(submissions_total or 0),
            "comments_total": int(comments_total or 0),
            "votes_total": int(votes_total or 0),
            "final_votes_total": int(final_votes_total or 0),
            "active_sessions": int(active_sessions or 0),
        }

    def users_total(self) -> int:
        # Cumulative users = addresses that have ever authenticated.
        # We create an AgentReputation row on successful auth_verify.
        with self._session() as db:
            return int(db.execute(select(func.count()).select_from(AgentReputationDB)).scalar_one() or 0)


def get_store() -> Store:
    # Default: if DATABASE_URL is set, use Postgres; otherwise fall back to in-memory.
    if settings.DATABASE_URL:
        return PostgresStore()
    return InMemoryStore()


store: Store = get_store()


def store_dep() -> Store:
    """
    FastAPI dependency for injecting the current Store.
    Keeping this indirection allows tests to override the dependency cleanly.
    """
    return store

