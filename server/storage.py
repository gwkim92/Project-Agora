from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass


def _lower_addr(address: str) -> str:
    return address.strip().lower()


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

        self.jobs: dict[str, dict] = {}
        self.submissions: dict[str, dict] = {}
        self.votes: dict[str, dict] = {}
        self.reputation: dict[str, dict] = {}

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
    def set_stake(self, address: str, amount: float) -> None:
        self.stakes_by_address[_lower_addr(address)] = float(amount)

    def get_stake(self, address: str) -> float:
        return float(self.stakes_by_address.get(_lower_addr(address), 0.0))

    # ---- Jobs/Submissions ----
    def create_job(self, job: dict) -> dict:
        job_id = str(uuid.uuid4())
        job = dict(job)
        job["id"] = job_id
        self.jobs[job_id] = job
        return job

    def list_jobs(self) -> list[dict]:
        # simple: return open jobs newest-first
        jobs = list(self.jobs.values())
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return [j for j in jobs if j.get("status") == "open"]

    def get_job(self, job_id: str) -> dict | None:
        return self.jobs.get(job_id)

    def create_submission(self, submission: dict) -> dict:
        sub_id = str(uuid.uuid4())
        submission = dict(submission)
        submission["id"] = sub_id
        self.submissions[sub_id] = submission
        return submission

    def list_submissions_for_job(self, job_id: str) -> list[dict]:
        subs = [s for s in self.submissions.values() if s.get("job_id") == job_id]
        subs.sort(key=lambda s: s.get("created_at", ""), reverse=False)
        return subs

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


store = InMemoryStore()

