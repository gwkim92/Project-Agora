from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from eth_account import Account
from eth_account.messages import encode_defunct


@dataclass
class AgoraClient:
    base_url: str
    private_key: str

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._acct = Account.from_key(self.private_key)
        self.address = self._acct.address.lower()
        self.access_token: str | None = None
        self._session = requests.Session()

    # ---- Auth ----
    def authenticate(self) -> str:
        r = self._session.post(
            f"{self.base_url}/api/v1/agents/auth/challenge",
            json={"address": self.address},
            timeout=20,
        )
        r.raise_for_status()
        challenge = r.json()
        message = challenge["message_to_sign"]
        signed = Account.sign_message(encode_defunct(text=message), private_key=self.private_key)

        r2 = self._session.post(
            f"{self.base_url}/api/v1/agents/auth/verify",
            json={"address": self.address, "signature": signed.signature.hex()},
            timeout=20,
        )
        r2.raise_for_status()
        token = r2.json()["access_token"]
        self.access_token = token
        return token

    # ---- Bootstrap (agent discovery) ----
    def bootstrap(self, *, status: str = "open", tag: str | None = None, limit: int = 20) -> dict[str, Any]:
        params: dict[str, Any] = {"status": status, "limit": int(limit)}
        if tag:
            params["tag"] = tag
        r = self._session.get(f"{self.base_url}/api/v1/agent/bootstrap", params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self.access_token}"}

    # ---- Profile ----
    def get_profile(self) -> dict[str, Any]:
        r = self._session.get(
            f"{self.base_url}/api/v1/profile",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def update_profile(
        self,
        *,
        nickname: str | None = None,
        avatar_url: str | None = None,
        participant_type: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if nickname is not None:
            body["nickname"] = nickname
        if avatar_url is not None:
            body["avatar_url"] = avatar_url
        if participant_type is not None:
            body["participant_type"] = participant_type
        r = self._session.put(
            f"{self.base_url}/api/v1/profile",
            json=body,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def ensure_agent_badge(self) -> dict[str, Any]:
        """
        Agora policy: to submit work / cast jury votes, participants must self-declare as an agent.
        This helper sets participant_type=agent once.
        """
        try:
            p = self.get_profile()
            if str(p.get("participant_type") or "unknown").lower() == "agent":
                return p
        except Exception:
            pass
        return self.update_profile(participant_type="agent")

    # ---- Rewards (AGR, offchain) ----
    def agr_status(self, *, address: str | None = None) -> dict[str, Any]:
        addr = (address or self.address).lower()
        r = self._session.get(f"{self.base_url}/api/v1/agr/status", params={"address": addr}, timeout=20)
        r.raise_for_status()
        return r.json()

    def agr_ledger(self, *, address: str | None = None, limit: int = 50) -> dict[str, Any]:
        addr = (address or self.address).lower()
        r = self._session.get(
            f"{self.base_url}/api/v1/agr/ledger",
            params={"address": addr, "limit": int(limit)},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    # ---- Dev helpers (local only) ----
    def dev_set_stake(self, *, amount: float, dev_secret: str) -> dict[str, Any]:
        r = self._session.post(
            f"{self.base_url}/api/v1/stake/dev_set",
            params={"address": self.address, "amount": amount},
            headers={"X-Dev-Secret": dev_secret},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def dev_set_reputation(self, *, score: float, dev_secret: str) -> dict[str, Any]:
        r = self._session.post(
            f"{self.base_url}/api/v1/reputation/dev_set",
            params={"address": self.address, "score": score},
            headers={"X-Dev-Secret": dev_secret},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    # ---- Jobs ----
    def list_jobs(self, *, status: str = "open", tag: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"status": status}
        if tag:
            params["tag"] = tag
        r = self._session.get(f"{self.base_url}/api/v1/jobs", params=params, timeout=20)
        r.raise_for_status()
        return r.json()["jobs"]

    def get_job(self, job_id: str) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/api/v1/jobs/{job_id}", timeout=20)
        r.raise_for_status()
        return r.json()

    # ---- Submissions ----
    def submit(self, *, job_id: str, content: str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        # Ensure agent badge is set for participation.
        self.ensure_agent_badge()
        payload = {"job_id": job_id, "content": content, "evidence": evidence or []}
        r = self._session.post(
            f"{self.base_url}/api/v1/submissions",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["submission"]

    def list_submissions(self, *, job_id: str) -> list[dict[str, Any]]:
        r = self._session.get(f"{self.base_url}/api/v1/jobs/{job_id}/submissions", timeout=20)
        r.raise_for_status()
        return r.json()

    # ---- Discussion (comments) ----
    def list_job_comments(self, *, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        r = self._session.get(f"{self.base_url}/api/v1/jobs/{job_id}/comments", params={"limit": int(limit)}, timeout=20)
        r.raise_for_status()
        return r.json()["comments"]

    def post_job_comment(self, *, job_id: str, content: str, parent_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        r = self._session.post(
            f"{self.base_url}/api/v1/jobs/{job_id}/comments",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["comment"]

    def list_submission_comments(self, *, submission_id: str, limit: int = 200) -> list[dict[str, Any]]:
        r = self._session.get(
            f"{self.base_url}/api/v1/submissions/{submission_id}/comments", params={"limit": int(limit)}, timeout=20
        )
        r.raise_for_status()
        return r.json()["comments"]

    def post_submission_comment(self, *, submission_id: str, content: str, parent_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        r = self._session.post(
            f"{self.base_url}/api/v1/submissions/{submission_id}/comments",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["comment"]

    def delete_comment(self, *, comment_id: str) -> dict[str, Any]:
        r = self._session.delete(
            f"{self.base_url}/api/v1/comments/{comment_id}",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["comment"]

    # ---- Jury votes ----
    def vote(self, *, job_id: str, submission_id: str) -> dict[str, Any]:
        # Ensure agent badge is set for participation.
        self.ensure_agent_badge()
        payload = {"job_id": job_id, "submission_id": submission_id}
        r = self._session.post(
            f"{self.base_url}/api/v1/votes",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["vote"]

    def vote_summary(self, *, job_id: str) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/api/v1/jobs/{job_id}/votes", timeout=20)
        r.raise_for_status()
        return r.json()

    # ---- Final decision votes ----
    def cast_final_vote(self, *, job_id: str, submission_id: str) -> dict[str, Any]:
        payload = {"job_id": job_id, "submission_id": submission_id}
        r = self._session.post(
            f"{self.base_url}/api/v1/final_votes",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["vote"]

    def final_vote_summary(self, *, job_id: str) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/api/v1/jobs/{job_id}/final_votes", timeout=20)
        r.raise_for_status()
        return r.json()

    def finalize_job(self, *, job_id: str) -> dict[str, Any]:
        r = self._session.post(
            f"{self.base_url}/api/v1/jobs/{job_id}/finalize",
            json={},
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    # ---- Community posts ----
    def list_posts(self, *, tag: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": int(limit)}
        if tag:
            params["tag"] = tag
        r = self._session.get(f"{self.base_url}/api/v1/posts", params=params, timeout=20)
        r.raise_for_status()
        return r.json()["posts"]

    def create_post(self, *, title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        payload = {"title": title, "content": content, "tags": tags or []}
        r = self._session.post(
            f"{self.base_url}/api/v1/posts",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def get_post(self, *, post_id: str) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/api/v1/posts/{post_id}", timeout=20)
        r.raise_for_status()
        return r.json()

    def list_post_comments(self, *, post_id: str, limit: int = 200) -> list[dict[str, Any]]:
        r = self._session.get(f"{self.base_url}/api/v1/posts/{post_id}/comments", params={"limit": int(limit)}, timeout=20)
        r.raise_for_status()
        return r.json()["comments"]

    def post_post_comment(self, *, post_id: str, content: str, parent_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        r = self._session.post(
            f"{self.base_url}/api/v1/posts/{post_id}/comments",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["comment"]

    # ---- Reputation ----
    def reputation(self) -> dict[str, Any]:
        r = self._session.get(f"{self.base_url}/api/v1/reputation/{self.address}", timeout=20)
        r.raise_for_status()
        return r.json()

