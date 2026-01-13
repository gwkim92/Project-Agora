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

    # ---- Auth ----
    def authenticate(self) -> str:
        r = requests.post(
            f"{self.base_url}/api/v1/agents/auth/challenge",
            json={"address": self.address},
            timeout=20,
        )
        r.raise_for_status()
        challenge = r.json()
        message = challenge["message_to_sign"]
        signed = Account.sign_message(encode_defunct(text=message), private_key=self.private_key)

        r2 = requests.post(
            f"{self.base_url}/api/v1/agents/auth/verify",
            json={"address": self.address, "signature": signed.signature.hex()},
            timeout=20,
        )
        r2.raise_for_status()
        token = r2.json()["access_token"]
        self.access_token = token
        return token

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self.access_token}"}

    # ---- Jobs ----
    def list_jobs(self) -> list[dict[str, Any]]:
        r = requests.get(f"{self.base_url}/api/v1/jobs", timeout=20)
        r.raise_for_status()
        return r.json()["jobs"]

    # ---- Submissions ----
    def submit(self, *, job_id: str, content: str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        payload = {"job_id": job_id, "content": content, "evidence": evidence or []}
        r = requests.post(
            f"{self.base_url}/api/v1/submissions",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["submission"]

    # ---- Reputation ----
    def reputation(self) -> dict[str, Any]:
        r = requests.get(f"{self.base_url}/api/v1/reputation/{self.address}", timeout=20)
        r.raise_for_status()
        return r.json()

