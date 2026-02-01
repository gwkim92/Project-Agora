from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.config import settings
from server.storage import Store


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json_bytes(obj: Any) -> bytes:
    # Canonical-ish: stable key ordering + compact separators.
    # ensure_ascii=False keeps UTF-8 stable for any unicode content.
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")


def build_job_snapshot(store: Store, job_id: str) -> dict[str, Any]:
    """
    Build a canonical snapshot payload for a job at close time.
    Offchain DB remains source-of-truth; this snapshot is meant for transparency + future anchoring.
    """
    job = store.get_job(job_id)
    if not job:
        raise KeyError("job not found")

    submissions = list(store.list_submissions_for_job(job_id))
    votes = list(store.list_votes_for_job(job_id))
    final_votes = list(store.list_final_votes_for_job(job_id))

    # Discussion threads
    job_comments = list(store.list_comments(target_type="job", target_id=job_id, limit=500))
    submission_comments: dict[str, list[dict]] = {}
    for sub in submissions:
        sid = str(sub.get("id") or "")
        if not sid:
            continue
        submission_comments[sid] = list(store.list_comments(target_type="submission", target_id=sid, limit=500))

    return {
        "schema_version": int(getattr(settings, "ANCHOR_SCHEMA_VERSION", 1)),
        "generated_at": _utc_now_iso(),
        "job": job,
        "submissions": submissions,
        "votes": votes,
        "final_votes": final_votes,
        "comments": {"job": job_comments, "submissions": submission_comments},
    }


def create_job_anchor_snapshot(*, store: Store, job_id: str) -> dict[str, Any]:
    """
    Create (idempotently) an offchain anchor batch row + write the snapshot JSON to a static URI.
    Returns the anchor batch dict.
    """
    # If already created, return existing.
    existing = store.get_anchor_batch(job_id)
    if existing:
        return existing

    snapshot = build_job_snapshot(store, job_id)
    data = _canonical_json_bytes(snapshot)

    root_hex = "0x" + hashlib.sha256(data).hexdigest()
    salt_hex = "0x" + secrets.token_hex(32)
    schema_version = int(getattr(settings, "ANCHOR_SCHEMA_VERSION", 1))

    # Write under server/static so it is served at /static/...
    static_dir = Path(__file__).resolve().parent / "static" / "anchors"
    static_dir.mkdir(parents=True, exist_ok=True)
    p = static_dir / f"{job_id}.json"
    p.write_bytes(data + b"\n")

    base = str(getattr(settings, "BASE_URL", "http://localhost:8000")).rstrip("/")
    uri = f"{base}/static/anchors/{job_id}.json"

    return store.upsert_anchor_batch(
        job_id=job_id,
        anchor_root=root_hex,
        anchor_uri=uri,
        schema_version=schema_version,
        salt=salt_hex,
    )

