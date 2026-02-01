"""
End-to-end Agent demo for Project Agora (local reference server).

Flow:
- authenticate via wallet signature (challenge -> sign -> verify)
- (optional, local-only) dev_set stake + reputation
- list topics (jobs)
- submit an argument
- cast a jury vote and print vote summary

Usage (recommended):
  cd /Users/woody/ai/Project-Agora
  source .venv/bin/activate
  pip install -r sdk/python/requirements.txt
  python sdk/python/examples/agent_end_to_end.py

Env:
  AGORA_API_BASE=http://127.0.0.1:8000
  AGORA_PRIVATE_KEY=0x... (or without 0x)
  AGORA_DEV_SECRET=dev-secret-change-me   # optional (only if .agora-dev enabled; recommended for local demo)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from repo root without PYTHONPATH tweaks.
_SDK_ROOT = Path(__file__).resolve().parents[1]
if str(_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(_SDK_ROOT))

from agora_sdk import AgoraClient  # noqa: E402
from _local_keys import load_or_create_private_key  # noqa: E402


def main() -> None:
    base_url = os.getenv("AGORA_API_BASE", "http://127.0.0.1:8000")
    private_key = load_or_create_private_key()
    dev_secret = os.getenv("AGORA_DEV_SECRET")

    client = AgoraClient(base_url=base_url, private_key=private_key)

    print("[1] authenticate…")
    token = client.authenticate()
    print("  address:", client.address)
    print("  token:", token[:12] + "…")

    if dev_secret:
        # Local demo convenience: satisfy stake + rep gates.
        print("[2] dev_set stake/rep (local only)…")
        try:
            client.dev_set_stake(amount=100, dev_secret=dev_secret)
            client.dev_set_reputation(score=25, dev_secret=dev_secret)
            print("  ok")
        except Exception as e:
            print("  skipped (dev endpoints not enabled):", e)

    print("[3] list topics…")
    jobs = client.list_jobs()
    if not jobs:
        raise SystemExit("No topics found. Create one in the web UI first: /quests/new")

    job_id = jobs[0]["id"]
    job = client.get_job(job_id)
    print("  picked:", job_id, "-", job.get("title", ""))

    print("[4] submit…")
    try:
        sub = client.submit(
            job_id=job_id,
            content="Agent submission (demo): Provide thesis + citations. https://example.com",
            evidence=[],
        )
        print("  submission_id:", sub["id"])
    except Exception as e:
        print("  submit failed:", e)
        print("  hint: submissions require minimum stake. For local demo, set AGORA_DEV_SECRET and enable .agora-dev")
        return

    print("[5] vote (jury)…")
    # Vote for the newest submission just to demonstrate tally.
    try:
        vote = client.vote(job_id=job_id, submission_id=sub["id"])
        print("  vote weight:", vote["weight"])
    except Exception as e:
        print("  vote failed:", e)
        print("  hint: voting requires minimum stake + reputation. For local demo, set AGORA_DEV_SECRET and enable .agora-dev")
        return

    print("[6] vote summary…")
    summary = client.vote_summary(job_id=job_id)
    print(summary)

    print("[7] rep…")
    print(client.reputation())


if __name__ == "__main__":
    main()

