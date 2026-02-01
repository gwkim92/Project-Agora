#!/usr/bin/env python3
"""
Headless "web session" demo:
Creates an Agora HttpOnly-cookie session by calling the Next.js BFF endpoints directly
and then performs a protected action (cast a final vote) via the BFF route.

This answers: "Can an agent use the service without a browser wallet extension?"
Yes: sign the server challenge with a private key, then use the cookie-backed session.

Usage:
  AGORA_WEB_BASE=http://127.0.0.1:3000 python scripts/headless_web_session_demo.py

Optional:
  AGORA_PRIVATE_KEY=0x...  (otherwise a random ephemeral key is generated)
  JOB_ID=...              (otherwise the first open job is used)
  SUBMISSION_ID=...       (otherwise the first submission is used, or a new one is created via API token)

Note:
  - This script does NOT require MetaMask/WalletConnect.
  - Gas is not sponsored; this script only uses signature auth + offchain actions.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests
from eth_account import Account
from eth_account.messages import encode_defunct


def _env(name: str, default: str) -> str:
    v = (os.getenv(name) or "").strip()
    return v if v else default


def _post_json(s: requests.Session, url: str, body: dict) -> dict:
    r = s.post(url, json=body, headers={"Origin": _env("AGORA_WEB_BASE", "http://127.0.0.1:3000")})
    r.raise_for_status()
    return r.json()


def main() -> int:
    web = _env("AGORA_WEB_BASE", "http://127.0.0.1:3000").rstrip("/")
    api = _env("AGORA_API_BASE", "http://127.0.0.1:8000").rstrip("/")

    pk = (os.getenv("AGORA_PRIVATE_KEY") or "").strip()
    if pk:
        acct = Account.from_key(pk)
    else:
        acct = Account.create()
        pk = acct.key.hex()

    print("[1] agent identity")
    print("  address:", acct.address)
    print("  private_key:", pk[:14] + "… (set AGORA_PRIVATE_KEY to reuse)")

    with requests.Session() as s:
        print("[2] challenge via BFF (/api/auth/challenge)")
        ch = _post_json(s, f"{web}/api/auth/challenge", {"address": acct.address})
        msg = str(ch.get("message_to_sign") or "")
        if not msg:
            raise RuntimeError("missing message_to_sign from challenge")
        sig = Account.sign_message(encode_defunct(text=msg), private_key=acct.key).signature.hex()

        print("[3] verify via BFF (/api/auth/verify) -> sets HttpOnly cookies")
        _post_json(s, f"{web}/api/auth/verify", {"address": acct.address, "signature": sig})

        print("[4] confirm session (/api/auth/me)")
        me = s.get(f"{web}/api/auth/me").json()
        print("  me:", me)
        if not me.get("authenticated"):
            raise RuntimeError("session not authenticated")

        # Pick a job.
        job_id = (os.getenv("JOB_ID") or "").strip()
        if not job_id:
            jobs = requests.get(f"{api}/api/v1/jobs?status=open").json().get("jobs") or []

            def _parse_rfc3339(ts: str | None) -> datetime | None:
                if not ts:
                    return None
                t = ts.strip()
                # support "Z"
                if t.endswith("Z"):
                    t = t[:-1] + "+00:00"
                try:
                    return datetime.fromisoformat(t)
                except Exception:
                    return None

            # If the API doesn't include final_vote_ends_at (older rows), approximate using default window.
            default_window = None
            try:
                c = requests.get(f"{api}/api/v1/governance/constitution").json()
                default_window = int(c.get("final_vote_window_seconds_default") or 0) or None
            except Exception:
                default_window = None

            now = datetime.now(timezone.utc)
            pick = None
            for j in jobs:
                ends = _parse_rfc3339(j.get("final_vote_ends_at"))
                if ends is None and default_window:
                    created = _parse_rfc3339(j.get("created_at"))
                    if created is not None:
                        ends = created + timedelta(seconds=default_window)
                if ends is not None and ends > now:
                    pick = j
                    break

            if pick is None:
                print("[5] no vote-eligible open job found; creating a fresh job (dev only)")
                # Create a job via direct API token auth (headless auth).
                ch2 = requests.post(f"{api}/api/v1/agents/auth/challenge", json={"address": acct.address}).json()
                msg2 = encode_defunct(text=str(ch2["message_to_sign"]))
                sig2 = Account.sign_message(msg2, private_key=acct.key).signature.hex()
                token = requests.post(f"{api}/api/v1/agents/auth/verify", json={"address": acct.address, "signature": sig2}).json()[
                    "access_token"
                ]
                dev = {"X-Dev-Secret": _env("AGORA_DEV_SECRET", "dev-secret-change-me")}
                requests.post(f"{api}/api/v1/stake/dev_set?address={acct.address}&amount=100", headers=dev).raise_for_status()
                requests.post(f"{api}/api/v1/reputation/dev_set?address={acct.address}&score=25", headers=dev).raise_for_status()

                created_job = requests.post(
                    f"{api}/api/v1/jobs",
                    json={
                        "title": "Headless web session demo",
                        "prompt": "Created by scripts/headless_web_session_demo.py",
                        "bounty_usdc": 0,
                        "tags": ["demo"],
                        "final_vote_window_seconds": 3600,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                ).json()
                job_id = str(created_job["id"])
            else:
                job_id = str(pick["id"])
        print("[5] job:", job_id)

        # Ensure there is at least one submission to vote on.
        sub_id = (os.getenv("SUBMISSION_ID") or "").strip()
        subs = requests.get(f"{api}/api/v1/jobs/{job_id}/submissions").json()
        if not sub_id:
            if subs:
                sub_id = str(subs[0]["id"])
            else:
                # Create a submission via direct API token auth (headless auth).
                ch2 = requests.post(f"{api}/api/v1/agents/auth/challenge", json={"address": acct.address}).json()
                msg2 = encode_defunct(text=str(ch2["message_to_sign"]))
                sig2 = Account.sign_message(msg2, private_key=acct.key).signature.hex()
                token = requests.post(f"{api}/api/v1/agents/auth/verify", json={"address": acct.address, "signature": sig2}).json()[
                    "access_token"
                ]
                # Give eligibility (dev only).
                dev = {"X-Dev-Secret": _env("AGORA_DEV_SECRET", "dev-secret-change-me")}
                requests.post(f"{api}/api/v1/stake/dev_set?address={acct.address}&amount=100", headers=dev).raise_for_status()
                requests.post(f"{api}/api/v1/reputation/dev_set?address={acct.address}&score=25", headers=dev).raise_for_status()
                created = requests.post(
                    f"{api}/api/v1/submissions",
                    json={"job_id": job_id, "content": "headless web session submission " + str(uuid.uuid4())[:8], "evidence": []},
                    headers={"Authorization": f"Bearer {token}"},
                ).json()["submission"]
                sub_id = str(created["id"])
                print("  created submission:", sub_id)

        print("[6] submission:", sub_id)

        # Cast final vote via cookie-backed BFF route.
        print("[7] cast final vote via BFF (/api/final_votes)")
        r = s.post(
            f"{web}/api/final_votes",
            json={"job_id": job_id, "submission_id": sub_id},
            headers={"Origin": web},
        )
        print("  status:", r.status_code)
        print("  body:", r.text)

        # If voting window is still open/closed, that's expected based on job timing.
        # We just demonstrate the authenticated cookie session reaching a protected route.

    print("[done] headless web session demo complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)

