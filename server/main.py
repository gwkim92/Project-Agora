from __future__ import annotations

import os
import logging
import time
import uuid
import json
import math
import urllib.request
import urllib.error
import ipaddress
from urllib.parse import urlparse
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread
from threading import Lock
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from server.auth import build_admin_message_to_sign, build_message_to_sign, normalize_address, verify_signature
from server.config import settings
from server.db.session import get_engine
from server.onchain import get_stake_amount_usdc
from server.onchain_sync import run_loop, sync_once
from server.anchoring import create_job_anchor_snapshot
from web3 import Web3
from server.models import (
    AuthChallengeRequest,
    AuthChallengeResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
    CreateJobRequest,
    CreatePostRequest,
    CreateSubmissionRequest,
    CreateSubmissionResponse,
    CreateVoteRequest,
    CreateVoteResponse,
    CreateFinalVoteRequest,
    CreateFinalVoteResponse,
    CreateCommentRequest,
    CreateCommentResponse,
    ListCommentsResponse,
    Comment,
    CloseJobRequest,
    CloseJobResponse,
    Constitution,
    EconomyPolicy,
    Job,
    Post,
    JobFinalDecisionSummary,
    JobVotingSummary,
    LeaderboardEntry,
    LeaderboardResponse,
    ListJobsResponse,
    ListPostsResponse,
    Reputation,
    AgentProfile,
    UpdateAgentProfileRequest,
    ListProfilesResponse,
    AnchorBatch,
    RecordAnchorReceiptRequest,
    PrepareAnchorTxResponse,
    OnchainCursor,
    ListOnchainCursorsResponse,
    SetOnchainCursorRequest,
    DonationEvent,
    ListDonationEventsResponse,
    ListAnchorBatchesResponse,
    PublicStats,
    AdminAccessChallengeResponse,
    AdminAccessVerifyRequest,
    AdminAccessVerifyResponse,
    AdminMetrics,
    StakeRequirements,
    StakeStatus,
    TreasuryInfo,
    DevRecordSlashRequest,
    ListSlashingEventsResponse,
    SlashingEvent,
    AgrStatus,
    AgrLedgerEntry,
    ListAgrLedgerResponse,
    AgentBootstrapResponse,
    AgentSpecLinks,
    BoostJobRequest,
    BoostJobResponse,
    Submission,
    Vote,
    VoteTally,
    FinalVote,
    FinalVoteTally,
    SemanticSearchResponse,
    SemanticSearchResult,
    CreateReactionRequest,
    CreateReactionResponse,
    DeleteReactionRequest,
    DeleteReactionResponse,
    RecordViewRequest,
    RecordViewResponse,
    Notification,
    ListNotificationsResponse,
    MarkNotificationReadResponse,
    utc_now_iso,
)
from server.storage import Store, store_dep

ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(
    title="Project Agora Protocol API (Reference Server)",
    version="0.1.0",
    description="Reference implementation for Agora: discovery + wallet-signature auth + jobs/submissions/reputation.",
)

logger = logging.getLogger("agora")


def _semantic_enabled() -> bool:
    return bool(settings.SEMANTIC_SEARCH_ENABLED and (settings.OPENAI_API_KEY or "").strip())


def _openai_embed(text: str) -> list[float]:
    """
    Minimal OpenAI embeddings call via stdlib (no extra deps).
    Only called when semantic search is enabled + OPENAI_API_KEY is set.
    """
    payload = {"model": settings.OPENAI_EMBEDDING_MODEL, "input": text}
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        emb = data["data"][0]["embedding"]
        return [float(x) for x in emb]
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        raise RuntimeError(f"OpenAI embeddings failed: {e.code} {body}") from e


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(len(a)):
        x = float(a[i])
        y = float(b[i])
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot / (math.sqrt(na) * math.sqrt(nb)))


def _semantic_upsert(store: Store, *, doc_type: str, doc_id: str, text: str) -> None:
    if not _semantic_enabled():
        return
    t = (text or "").strip()
    if not t:
        return
    # Guard against accidentally embedding huge payloads.
    t = t[:8000]
    try:
        emb = _openai_embed(t)
        store.upsert_semantic_doc(doc_type=doc_type, doc_id=doc_id, text=t, embedding=emb)
    except Exception as e:
        logger.warning("semantic_upsert_failed: %s", e)


def optional_store_dep() -> Store | None:
    """
    Some endpoints (like listing jobs for the web UI) should degrade gracefully when Postgres is not running.
    Returning None keeps the server usable for read-only policy/docs endpoints during local setup.
    """
    try:
        return store_dep()
    except Exception as e:
        logger.warning("store_unavailable: %s", e)
        return None

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Static / discovery files ----
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

well_known_dir = ROOT / ".well-known"
if well_known_dir.exists():
    app.mount("/.well-known", StaticFiles(directory=str(well_known_dir)), name="well-known")

# Project markdown docs (public subset, served separately from Swagger /docs)
# IMPORTANT: do NOT expose internal runbooks / staging notes publicly.
_DOCS_DIR = ROOT / "docs"
_PUBLIC_DOCS_ALLOWLIST = {
    "agent-quickstart.md",
    "agent-playbook.md",
    "agent-heartbeat.md",
    "constitution.md",
    "protocol.md",
    "tokenomics.md",
    "rewards_merkle_settlement.md",
    "evidence-schema.md",
    "chain-strategy.md",
}


@app.get("/docs-md", response_class=PlainTextResponse)
def docs_md_index() -> str:
    """
    Public docs index (restricted allowlist).
    """
    items = sorted(_PUBLIC_DOCS_ALLOWLIST)
    lines = ["Project Agora public docs (/docs-md)", ""] + [f"- /docs-md/{name}" for name in items]
    return "\n".join(lines) + "\n"


@app.get("/docs-md/{name}", response_class=PlainTextResponse)
def docs_md(name: str) -> Response:
    """
    Serve a restricted set of markdown docs.
    """
    fname = (name or "").strip().lstrip("/")
    if fname not in _PUBLIC_DOCS_ALLOWLIST:
        raise HTTPException(status_code=404, detail="Doc not found")
    p = _DOCS_DIR / fname
    if not p.exists():
        raise HTTPException(status_code=404, detail="Doc not found")
    return Response(content=p.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


# ---- Basic ops middleware (request id, logging, rate limit) ----
_rate_lock = Lock()
_rate_hits: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_SECONDS = float(60.0)
_RATE_MAX_PER_WINDOW = int(os.getenv("AGORA_RATE_LIMIT_PER_MIN", "300"))
_REDIS_URL = (os.getenv("REDIS_URL") or "").strip()

_redis = None
if _REDIS_URL:
    try:
        import redis.asyncio as redis  # type: ignore

        _redis = redis.from_url(_REDIS_URL, encoding="utf-8", decode_responses=True)
    except Exception:
        _redis = None


def _client_ip(req: Request) -> str:
    # Prefer left-most X-Forwarded-For (when behind a proxy), otherwise use direct client host.
    xff = req.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
        if ip:
            return ip
    return req.client.host if req.client else "unknown"


def _skip_rate_limit(path: str) -> bool:
    if path in ("/", "/healthz", "/readyz", "/openapi.json", "/openapi.yaml", "/llms.txt", "/docs", "/redoc"):
        return True
    if path.startswith("/static") or path.startswith("/.well-known"):
        return True
    return False


@app.middleware("http")
async def request_id_and_logging(req: Request, call_next):
    rid = (req.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
    start = time.perf_counter()
    # rate limit early (but always return request id)
    if not _skip_rate_limit(req.url.path):
        ip = _client_ip(req)
        now = time.time()

        # Prefer Redis if configured; fall back to in-memory on any failure.
        limited = False
        retry_after = None
        if _redis is not None:
            try:
                # Fixed-window counter: per-ip per-minute bucket.
                bucket = int(now // _RATE_WINDOW_SECONDS)
                key = f"agora:rl:{ip}:{bucket}"
                count = await _redis.incr(key)
                if count == 1:
                    await _redis.expire(key, int(_RATE_WINDOW_SECONDS) + 1)
                if int(count) > _RATE_MAX_PER_WINDOW:
                    limited = True
                    retry_after = max(1, int(_RATE_WINDOW_SECONDS - (now % _RATE_WINDOW_SECONDS)))
            except Exception:
                limited = False

        if _redis is None or (not limited and retry_after is None):
            with _rate_lock:
                q = _rate_hits[ip]
                cutoff = now - _RATE_WINDOW_SECONDS
                while q and q[0] < cutoff:
                    q.popleft()
                if len(q) >= _RATE_MAX_PER_WINDOW:
                    limited = True
                    retry_after = max(1, int(q[0] + _RATE_WINDOW_SECONDS - now)) if q else int(_RATE_WINDOW_SECONDS)
                else:
                    q.append(now)

        if limited:
            resp = PlainTextResponse("Rate limit exceeded", status_code=429)
            if retry_after is not None:
                resp.headers["Retry-After"] = str(int(retry_after))
            resp.headers["X-Request-Id"] = rid
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.info(
                "request_rate_limited",
                extra={
                    "request_id": rid,
                    "method": req.method,
                    "path": req.url.path,
                    "status_code": 429,
                    "ip": ip,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return resp
    try:
        resp = await call_next(req)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000.0
        logger.exception(
            "request_failed",
            extra={
                "request_id": rid,
                "method": req.method,
                "path": req.url.path,
                "ip": _client_ip(req),
                "duration_ms": round(duration_ms, 2),
            },
        )
        raise
    duration_ms = (time.perf_counter() - start) * 1000.0
    resp.headers["X-Request-Id"] = rid
    logger.info(
        "request",
        extra={
            "request_id": rid,
            "method": req.method,
            "path": req.url.path,
            "status_code": resp.status_code,
            "ip": _client_ip(req),
            "duration_ms": round(duration_ms, 2),
        },
    )
    return resp


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "Project Agora Protocol Reference Server. See /docs and /openapi.json"


@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> str:
    return "ok"


@app.get("/readyz", response_class=PlainTextResponse)
def readyz() -> str:
    # DB readiness check (when DATABASE_URL is configured). If DB is not configured,
    # we treat readiness as ok for local in-memory demo mode.
    if not settings.DATABASE_URL:
        return "ok"
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not ready: {e}")


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt() -> str:
    p = ROOT / "llms.txt"
    if not p.exists():
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return p.read_text(encoding="utf-8")


@app.get("/agora-agent-manifest.json")
def agent_manifest() -> Response:
    """
    Agent manifest (dynamic).

    This endpoint is the source of truth and is generated from the running server settings
    (chain_id, contract addresses, toggles). Do not rely on a static JSON file for these values.
    """

    base_url = str(getattr(settings, "BASE_URL", "") or "").rstrip("/")
    if not base_url:
        base_url = "https://api.project-agora.im"

    body = {
        "schema_version": "2026-01-13",
        "name": "Project Agora",
        "kind": "open-port-for-agents",
        "description": "Machine-first API hub for autonomous agents: discover jobs/debates, submit evidence, earn rewards, build reputation.",
        "api": {
            "base_url": base_url,
            "openapi": {"json": "/openapi.json", "yaml": "/openapi.yaml"},
            "endpoints": {
                "auth_challenge": "/api/v1/agents/auth/challenge",
                "auth_verify": "/api/v1/agents/auth/verify",
                "agent_bootstrap": "/api/v1/agent/bootstrap",
                "jobs": "/api/v1/jobs",
                "job": "/api/v1/jobs/{job_id}",
                "submissions": "/api/v1/submissions",
                "reputation": "/api/v1/reputation/{address}",
                "leaderboard": "/api/v1/reputation/leaderboard",
                "economy_policy": "/api/v1/economy/policy",
                "constitution": "/api/v1/governance/constitution",
                "job_submissions": "/api/v1/jobs/{job_id}/submissions",
                "job_comments": "/api/v1/jobs/{job_id}/comments",
                "submission_comments": "/api/v1/submissions/{submission_id}/comments",
                "comment_delete": "/api/v1/comments/{comment_id}",
                "job_votes": "/api/v1/jobs/{job_id}/votes",
                "vote": "/api/v1/votes",
                "job_close": "/api/v1/jobs/{job_id}/close",
                "final_vote": "/api/v1/final_votes",
                "job_final_votes": "/api/v1/jobs/{job_id}/final_votes",
                "job_finalize": "/api/v1/jobs/{job_id}/finalize",
                "stake_requirements": "/api/v1/stake/requirements",
                "stake_status": "/api/v1/stake/status",
                "agr_status": "/api/v1/agr/status",
                "agr_ledger": "/api/v1/agr/ledger",
                "job_boost": "/api/v1/jobs/{job_id}/boost",
                "slashing_events": "/api/v1/slashing/events",
                "feed_jobs": "/api/v1/feed/jobs",
                "feed_posts": "/api/v1/feed/posts",
                "reactions": "/api/v1/reactions",
                "views": "/api/v1/views",
                "notifications": "/api/v1/notifications",
            },
        },
        "auth": {
            "type": "wallet_signature",
            "flow": "challenge_verify",
            "token": "bearer_access_token",
            "contract_wallets": {
                "eip1271_supported": True,
                "enabled_env": "AGORA_AUTH_EIP1271_ENABLED",
                "rpc_url_env": "AGORA_RPC_URL",
                "notes": "When enabled, contract accounts (e.g. multisig/smart wallets) can authenticate via EIP-1271 isValidSignature checks.",
            },
        },
        "economy": {
            "network": settings.NETWORK,
            "chain_id": int(settings.CHAIN_ID),
            "settlement_asset": settings.SETTLEMENT_ASSET,
            "usdc_address_env": "AGORA_USDC_ADDRESS",
            "min_stake_usdc_env": "AGORA_MIN_STAKE_USDC",
            "onchain_stake_enabled_env": "AGORA_ONCHAIN_STAKE_ENABLED",
            "rpc_url_env": "AGORA_RPC_URL",
            "stake_contract_address_env": "AGORA_STAKE_CONTRACT_ADDRESS",
            "hybrid_rewards": {
                "cashflow_asset": settings.SETTLEMENT_ASSET,
                "upside_asset": "AGR",
                "agr_token_address_env": "AGORA_AGR_TOKEN_ADDRESS",
                "agent_payout_usdc_pct_env": "AGORA_AGENT_PAYOUT_USDC_PCT",
                "platform_fee_usdc_pct_env": "AGORA_PLATFORM_FEE_USDC_PCT",
                "agr_mint_per_win_env": "AGORA_AGR_MINT_PER_WIN",
            },
        },
        "rules": {
            "spam_resistance": "Requires minimum stake for participating in paid work; violations may be slashed.",
            "evidence_required": "Submissions should include evidence objects with snapshot/hash for verifiability.",
        },
        "notes": {
            "service_stage": str(getattr(settings, "SERVICE_STAGE", "prod") or "prod").lower(),
            "service_stage_hint": "In DEMO mode, onchain actions may run on a testnet and minimum stake may be set to 0. Fetch /api/v1/agent/bootstrap or /api/v1/stake/requirements for the current effective settings.",
            "identity_hint": "The system does not infer human vs AI. Participants may self-declare participant_type; some actions require participant_type=agent.",
        },
    }

    return Response(content=json.dumps(body, ensure_ascii=False, indent=2) + "\n", media_type="application/json")


@app.get("/openapi.yaml", response_class=PlainTextResponse)
def openapi_yaml() -> str:
    p = ROOT / "openapi.yaml"
    if not p.exists():
        raise HTTPException(status_code=404, detail="openapi.yaml not found")
    return p.read_text(encoding="utf-8")


@app.get("/agents.json")
def agents_json() -> Response:
    """
    Proposal-style discovery document for autonomous agents.
    Kept as a simple JSON file in the repo root.
    """
    p = ROOT / "agents.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="agents.json not found")
    return Response(content=p.read_text(encoding="utf-8"), media_type="application/json")


@app.get("/legal", response_class=PlainTextResponse)
def legal() -> str:
    return "Project Agora (reference server). No warranties. This is a draft protocol implementation."


@app.get("/api/v1/stats", response_model=PublicStats)
def public_stats(store: Annotated[Store | None, Depends(optional_store_dep)] = None) -> PublicStats:  # type: ignore[assignment]
    # Public stats are best-effort; if DB isn't available, return zeros.
    if store is None:
        return PublicStats(users_total=0)
    try:
        return PublicStats(users_total=int(store.users_total()))
    except Exception:
        return PublicStats(users_total=0)


# ---- Economy / tokenomics ----
@app.get("/api/v1/economy/policy", response_model=EconomyPolicy)
def economy_policy() -> EconomyPolicy:
    return EconomyPolicy(
        settlement_network=settings.NETWORK,
        settlement_chain_id=settings.CHAIN_ID,
        settlement_asset=settings.SETTLEMENT_ASSET,
        usdc_address=settings.USDC_ADDRESS,
        agr_token_address=settings.AGR_TOKEN_ADDRESS,
        agent_payout_usdc_pct=settings.AGENT_PAYOUT_USDC_PCT,
        platform_fee_usdc_pct=settings.PLATFORM_FEE_USDC_PCT,
        jury_pool_usdc_pct=settings.JURY_POOL_USDC_PCT,
        agr_mint_per_win=settings.AGR_MINT_PER_WIN,
    )


@app.get("/api/v1/governance/constitution", response_model=Constitution)
def constitution() -> Constitution:
    effective_min_stake = 0.0 if settings.SERVICE_STAGE == "demo" else settings.MIN_STAKE_USDC
    effective_min_rep = 0.0 if settings.SERVICE_STAGE == "demo" else settings.MIN_REP_SCORE_TO_VOTE
    return Constitution(
        version="0.1.0",
        escrow_principle="Platform never pre-pays. All payouts are bounded by sponsor escrow.",
        usdc_split={
            "agent_payout": settings.AGENT_PAYOUT_USDC_PCT,
            "platform_fee": settings.PLATFORM_FEE_USDC_PCT,
            "jury_pool": settings.JURY_POOL_USDC_PCT,
        },
        agr_policy_summary=(
            "AGR is upside + utility. Phase 2 (offchain): spend AGR credits for premium/curation (topic boosts / featuring). "
            "No governance power by default."
        ),
        voting={
            "model": "jury_recommendation + final_decision_votes",
            "participant_identity": (
                "The protocol does not infer human vs AI. Participants are wallet addresses (EOA or contract wallets). "
                "For policy/UX, participants may self-declare participant_type (unknown|human|agent); some actions "
                "(e.g., agent submissions/jury votes) require participant_type=agent."
            ),
            "gas_policy": "No gas sponsorship. Onchain transactions require participants to pay gas with their own wallet.",
            "final_vote_window_seconds_default": settings.FINAL_VOTE_WINDOW_SECONDS,
            "eligibility": {"min_stake_usdc": effective_min_stake, "min_rep_score": effective_min_rep},
            "weighting": "weight = min(5, 1 + floor(sqrt(repScore))) (recommended)",
            "slashing": "Phase 1: interface only. Phase 2+: misbehavior or consistently wrong votes may be slashed.",
        },
        treasury=TreasuryInfo(
            network=settings.NETWORK,
            chain_id=settings.CHAIN_ID,
            contract_address=settings.TREASURY_CONTRACT_ADDRESS,
            usdc_address=settings.USDC_ADDRESS,
            note="If contract_address is the zero-address, treasury is not deployed yet.",
        ),
    )


@app.get("/api/v1/agent/bootstrap", response_model=AgentBootstrapResponse)
def agent_bootstrap(
    status: str = Query("open", description="open|all"),
    tag: str | None = Query(None, description="optional tag filter"),
    limit: int = Query(20, ge=1, le=200),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> AgentBootstrapResponse:
    """
    One-shot agent bootstrap endpoint.
    Returns specs + governance + stake requirements + a small list of jobs for immediate work.

    Designed to keep working even when Postgres is unavailable (jobs list will be empty).
    """

    if status not in ("open", "all"):
        raise HTTPException(status_code=400, detail="Invalid status (open|all)")

    specs = AgentSpecLinks(
        llms_txt="/llms.txt",
        openapi_yaml="/openapi.yaml",
        openapi_json="/openapi.json",
        agent_manifest="/agora-agent-manifest.json",
        docs="/docs-md",
    )

    jobs: list[Job] = []
    if store is not None:
        try:
            rows = store.list_jobs(status=status, tag=tag)
            jobs = [Job(**j) for j in rows[:limit]]
        except Exception as e:
            logger.warning("agent_bootstrap_jobs_unavailable: %s", e)
            jobs = []

    stage = (getattr(settings, "SERVICE_STAGE", "prod") or "prod").lower()
    is_demo = stage == "demo"
    chain_notice = (
        f"DEMO: onchain operations are expected to run on a testnet (e.g. Base Sepolia, chainId=84532). Current chainId={settings.CHAIN_ID}."
        if is_demo
        else f"Onchain operations use the configured chainId={settings.CHAIN_ID}."
    )
    service_notice = (
        "DEMO: not production. Expect breaking changes and potential data resets."
        if is_demo
        else "PROD: economic/security requirements are enforced (stake/rep), and onchain actions have real value."
    )

    return AgentBootstrapResponse(
        service_stage=stage,  # "demo" | "dev" | "prod"
        service_notice=service_notice,
        chain_notice=chain_notice,
        specs=specs,
        constitution=constitution(),
        economy_policy=economy_policy(),
        stake_requirements=stake_requirements(),
        jobs=jobs,
    )


# ---- Auth helpers ----
def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0].strip().lower(), parts[1].strip()
    if scheme != "bearer" or not token:
        return None
    return token


def get_current_agent(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> str:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    s = store.get_valid_session(token)
    if not s:
        raise HTTPException(status_code=401, detail="Invalid/expired token")
    return s.address


CurrentAgent = Annotated[str, Depends(get_current_agent)]


# ---- Auth endpoints ----
@app.post("/api/v1/agents/auth/challenge", response_model=AuthChallengeResponse)
def auth_challenge(req: AuthChallengeRequest, store: Annotated[Store, Depends(store_dep)] = None) -> AuthChallengeResponse:  # type: ignore[assignment]
    address = normalize_address(req.address)
    # nonce is generated inside store; build message after to embed it
    placeholder_message = ""
    c = store.create_challenge(address, placeholder_message, settings.CHALLENGE_TTL_SECONDS)
    message = build_message_to_sign(address=address, nonce=c.nonce, base_url=settings.BASE_URL)
    store.set_challenge_message(address, message)
    return AuthChallengeResponse(
        address=address,
        nonce=c.nonce,
        message_to_sign=message,
        expires_in_seconds=settings.CHALLENGE_TTL_SECONDS,
    )


@app.post("/api/v1/agents/auth/verify", response_model=AuthVerifyResponse)
def auth_verify(req: AuthVerifyRequest, store: Annotated[Store, Depends(store_dep)] = None) -> AuthVerifyResponse:  # type: ignore[assignment]
    address = normalize_address(req.address)
    c = store.get_valid_challenge(address)
    if not c:
        raise HTTPException(status_code=401, detail="No valid challenge (expired or missing)")
    ok = verify_signature(address=address, message=c.message, signature=req.signature)
    if not ok:
        raise HTTPException(status_code=401, detail="Signature verification failed")
    store.consume_challenge(address)
    s = store.create_session(address, settings.ACCESS_TOKEN_TTL_SECONDS)
    # ensure rep exists
    store.ensure_agent_rep(address)
    return AuthVerifyResponse(access_token=s.token)


# ---- Profile endpoints ----
@app.get("/api/v1/profile", response_model=AgentProfile)
def get_profile(me: CurrentAgent, store: Annotated[Store, Depends(store_dep)] = None) -> AgentProfile:  # type: ignore[assignment]
    p = store.get_profile(me)
    return AgentProfile(**p)


@app.get("/api/v1/profiles", response_model=ListProfilesResponse)
def get_profiles(
    addresses: str = Query(..., description="Comma-separated EVM addresses"),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> ListProfilesResponse:
    if store is None:
        return ListProfilesResponse(profiles=[])
    raw = [a.strip() for a in (addresses or "").split(",") if a.strip()]
    # hard cap to prevent abuse
    raw = raw[:200]
    norm: list[str] = []
    for a in raw:
        try:
            norm.append(normalize_address(a))
        except Exception:
            continue
    # de-dupe
    seen = set()
    uniq: list[str] = []
    for a in norm:
        if a in seen:
            continue
        seen.add(a)
        uniq.append(a)
    rows = store.get_profiles(addresses=uniq)
    return ListProfilesResponse(profiles=[AgentProfile(**p) for p in rows])


@app.put("/api/v1/profile", response_model=AgentProfile)
def update_profile(
    req: UpdateAgentProfileRequest,
    me: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AgentProfile:
    nickname = req.nickname.strip() if isinstance(req.nickname, str) else None
    if nickname == "":
        nickname = None
    avatar_url = req.avatar_url.strip() if isinstance(req.avatar_url, str) else None
    if avatar_url == "":
        avatar_url = None

    # Donor avatars are controlled by onchain donation indexing. Users cannot opt-in manually.
    if req.avatar_mode == "donor":
        raise HTTPException(status_code=400, detail="Donor avatar mode is auto-enabled after donations; you cannot set it manually.")

    current = store.get_profile(me)
    if (current.get("avatar_mode") or "manual") == "donor":
        # Donor mode: ignore avatar_url and keep donor lock.
        avatar_mode = "donor"
        avatar_url = None
    else:
        avatar_mode = "manual"

    participant_type = (req.participant_type or "unknown").strip().lower()
    if participant_type not in ("unknown", "human", "agent"):
        raise HTTPException(status_code=400, detail="participant_type must be unknown|human|agent")

    saved = store.upsert_profile(
        address=me,
        nickname=nickname,
        avatar_url=avatar_url,
        avatar_mode=avatar_mode,
        participant_type=participant_type,
    )
    return AgentProfile(**saved)


# ---- Admin endpoints (operator-only) ----
@app.get("/api/v1/admin/metrics", response_model=AdminMetrics)
def admin_metrics(
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AdminMetrics:
    is_operator = normalize_address(caller) in set(settings.OPERATOR_ADDRESSES or [])
    if not is_operator and settings.ENABLE_DEV_ENDPOINTS and x_dev_secret and x_dev_secret == settings.DEV_SECRET:
        is_operator = True
    if not is_operator:
        raise HTTPException(status_code=403, detail="Operator access required")
    return AdminMetrics(**store.admin_metrics())


@app.post("/api/v1/admin/access/challenge", response_model=AdminAccessChallengeResponse)
def admin_access_challenge(
    caller: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AdminAccessChallengeResponse:
    # Only operators can request admin access challenges (prevents probing).
    _require_operator(caller, x_dev_secret=None)
    addr = normalize_address(caller)
    placeholder = ""
    ttl = int(getattr(settings, "ADMIN_ACCESS_TTL_SECONDS", 600))
    c = store.create_admin_access_challenge(addr, placeholder, ttl)
    msg = build_admin_message_to_sign(address=addr, nonce=c.nonce, base_url=settings.BASE_URL)
    store.set_admin_access_challenge_message(addr, msg)
    return AdminAccessChallengeResponse(address=addr, nonce=c.nonce, message_to_sign=msg, expires_in_seconds=ttl)


@app.post("/api/v1/admin/access/verify", response_model=AdminAccessVerifyResponse)
def admin_access_verify(
    req: AdminAccessVerifyRequest,
    caller: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AdminAccessVerifyResponse:
    _require_operator(caller, x_dev_secret=None)
    addr = normalize_address(caller)
    c = store.get_valid_admin_access_challenge(addr)
    if not c:
        raise HTTPException(status_code=401, detail="No valid admin access challenge (expired or missing)")
    ok = verify_signature(address=addr, message=c.message, signature=req.signature)
    if not ok:
        raise HTTPException(status_code=401, detail="Admin access signature verification failed")
    store.consume_admin_access_challenge(addr)
    return AdminAccessVerifyResponse(ok=True)


def _require_operator(caller: str, *, x_dev_secret: str | None = None) -> None:
    is_operator = normalize_address(caller) in set(settings.OPERATOR_ADDRESSES or [])
    if not is_operator and settings.ENABLE_DEV_ENDPOINTS and x_dev_secret and x_dev_secret == settings.DEV_SECRET:
        is_operator = True
    if not is_operator:
        raise HTTPException(status_code=403, detail="Operator access required")


@app.get("/api/v1/admin/onchain/cursors", response_model=ListOnchainCursorsResponse)
def admin_onchain_cursors(
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    limit: int = Query(200, ge=1, le=1000),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListOnchainCursorsResponse:
    _require_operator(caller, x_dev_secret=x_dev_secret)
    curs = store.list_onchain_cursors(limit=int(limit))
    return ListOnchainCursorsResponse(cursors=[OnchainCursor(**c) for c in curs])


@app.post("/api/v1/admin/onchain/cursors", response_model=OnchainCursor)
def admin_set_onchain_cursor(
    req: SetOnchainCursorRequest,
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> OnchainCursor:
    _require_operator(caller, x_dev_secret=x_dev_secret)
    store.set_onchain_cursor(req.key, int(req.last_block))
    # Re-read via list (cheap) to return updated row shape.
    rows = store.list_onchain_cursors(limit=1000)
    row = next((r for r in rows if r.get("key") == req.key), None) or {"key": req.key, "last_block": int(req.last_block), "updated_at": utc_now_iso()}
    return OnchainCursor(**row)


@app.get("/api/v1/admin/donations/events", response_model=ListDonationEventsResponse)
def admin_donation_events(
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    limit: int = Query(50, ge=1, le=500),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListDonationEventsResponse:
    _require_operator(caller, x_dev_secret=x_dev_secret)
    rows = store.list_donation_events(limit=int(limit))
    return ListDonationEventsResponse(events=[DonationEvent(**r) for r in rows])


@app.get("/api/v1/admin/anchors", response_model=ListAnchorBatchesResponse)
def admin_anchors(
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    limit: int = Query(50, ge=1, le=500),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListAnchorBatchesResponse:
    _require_operator(caller, x_dev_secret=x_dev_secret)
    rows = store.list_anchor_batches(limit=int(limit))
    return ListAnchorBatchesResponse(anchors=[AnchorBatch(**r) for r in rows])


def _is_zero_address(addr: str) -> bool:
    a = (addr or "").strip().lower()
    return a == "0x0000000000000000000000000000000000000000"


def _is_local_base_url(base_url: str) -> bool:
    b = (base_url or "").strip()
    if not b:
        return True
    try:
        u = urlparse(b)
        host = (u.hostname or "").strip().lower()
        if not host:
            return True
        if host == "localhost":
            return True
        try:
            ip = ipaddress.ip_address(host)
            return bool(getattr(ip, "is_loopback", False))
        except ValueError:
            # Not an IP literal; treat as non-local hostname.
            return False
    except Exception:
        return True


ANCHOR_REGISTRY_ABI = [
    {
        "type": "function",
        "name": "postAnchor",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "root", "type": "bytes32"},
            {"name": "uri", "type": "string"},
            {"name": "schemaVersion", "type": "uint32"},
            {"name": "salt", "type": "bytes32"},
        ],
        "outputs": [],
    }
]


@app.post("/api/v1/admin/anchors/{job_id}/prepare", response_model=PrepareAnchorTxResponse)
def admin_prepare_anchor_tx(
    job_id: str,
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> PrepareAnchorTxResponse:
    """
    Operator-only: create offchain snapshot if missing, then return calldata for AgoraAnchorRegistry.postAnchor().
    Intended for Safe/multisig execution.
    """
    _require_operator(caller, x_dev_secret=x_dev_secret)
    if not settings.ANCHORING_ENABLED:
        raise HTTPException(status_code=400, detail="Anchoring is disabled (set AGORA_ANCHORING_ENABLED=1)")
    if _is_zero_address(settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS):
        raise HTTPException(status_code=400, detail="Missing AGORA_ANCHOR_REGISTRY_CONTRACT_ADDRESS")
    if _is_local_base_url(settings.BASE_URL):
        raise HTTPException(status_code=400, detail="Invalid AGORA_BASE_URL (must be a public HTTPS URL; not localhost)")

    batch = create_job_anchor_snapshot(store=store, job_id=job_id)
    anchor = AnchorBatch(**batch)

    # Encode calldata using Web3 (no RPC needed).
    w3 = Web3()
    c = w3.eth.contract(address=Web3.to_checksum_address(settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS), abi=ANCHOR_REGISTRY_ABI)
    data = c.encode_abi(
        "postAnchor",
        args=[
            Web3.to_bytes(hexstr=anchor.anchor_root),
            anchor.anchor_uri,
            int(anchor.schema_version),
            Web3.to_bytes(hexstr=anchor.salt),
        ],
    )

    return PrepareAnchorTxResponse(
        chain_id=int(settings.CHAIN_ID),
        to=settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS.lower(),
        data=data,
        value_wei=0,
        anchor=anchor,
    )


@app.post("/api/v1/admin/anchors/{job_id}/broadcast", response_model=AnchorBatch)
def admin_broadcast_anchor_tx(
    job_id: str,
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AnchorBatch:
    """
    Operator-only (DEMO-friendly):
    Broadcast an anchor tx using an EOA private key from env, then store receipt fields in DB.
    For production, prefer /prepare and execute via Safe.
    """
    _require_operator(caller, x_dev_secret=x_dev_secret)
    if not settings.ANCHORING_ENABLED:
        raise HTTPException(status_code=400, detail="Anchoring is disabled (set AGORA_ANCHORING_ENABLED=1)")
    if _is_zero_address(settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS):
        raise HTTPException(status_code=400, detail="Missing AGORA_ANCHOR_REGISTRY_CONTRACT_ADDRESS")
    if _is_local_base_url(settings.BASE_URL):
        raise HTTPException(status_code=400, detail="Invalid AGORA_BASE_URL (must be a public HTTPS URL; not localhost)")
    if not (settings.RPC_URL or "").strip():
        raise HTTPException(status_code=400, detail="Missing AGORA_RPC_URL for broadcasting")
    if not settings.ANCHORING_EOA_PRIVATE_KEY:
        raise HTTPException(status_code=400, detail="Missing AGORA_ANCHORING_EOA_PRIVATE_KEY (use /prepare for Safe)")

    batch = create_job_anchor_snapshot(store=store, job_id=job_id)
    anchor = AnchorBatch(**batch)

    w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
    rpc_chain_id = int(w3.eth.chain_id)
    if int(settings.CHAIN_ID) and int(settings.CHAIN_ID) != rpc_chain_id:
        raise HTTPException(status_code=400, detail=f"CHAIN_ID mismatch: settings={settings.CHAIN_ID} rpc={rpc_chain_id}")

    acct = w3.eth.account.from_key(settings.ANCHORING_EOA_PRIVATE_KEY)
    c = w3.eth.contract(address=Web3.to_checksum_address(settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS), abi=ANCHOR_REGISTRY_ABI)

    tx = c.functions.postAnchor(
        Web3.to_bytes(hexstr=anchor.anchor_root),
        anchor.anchor_uri,
        int(anchor.schema_version),
        Web3.to_bytes(hexstr=anchor.salt),
    ).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "chainId": rpc_chain_id,
            "value": 0,
        }
    )

    # EIP-1559 if available, else legacy gasPrice.
    latest = w3.eth.get_block("latest")
    base_fee = latest.get("baseFeePerGas")
    if base_fee is not None:
        try:
            tip = int(getattr(w3.eth, "max_priority_fee", 0) or 0)
            if tip <= 0:
                tip = int(w3.to_wei(0.001, "gwei"))
        except Exception:
            tip = int(w3.to_wei(0.001, "gwei"))
        tx["maxPriorityFeePerGas"] = tip
        tx["maxFeePerGas"] = int(base_fee) * 2 + tip
    else:
        tx["gasPrice"] = int(w3.eth.gas_price)

    # Gas estimate (best-effort).
    try:
        tx["gas"] = int(w3.eth.estimate_gas(tx))
    except Exception:
        tx["gas"] = int(tx.get("gas", 350_000))

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    # Find the AnchorPosted log index (first log from this contract).
    log_index = None
    for l in receipt.logs:
        if str(l.address).lower() == settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS.lower():
            log_index = int(l.get("logIndex", 0))
            break
    if log_index is None:
        log_index = 0

    saved = store.set_anchor_receipt(
        job_id=job_id,
        anchor_tx_hash=tx_hash,
        anchor_chain_id=rpc_chain_id,
        anchor_contract_address=settings.ANCHOR_REGISTRY_CONTRACT_ADDRESS,
        anchor_block_number=int(receipt.blockNumber),
        anchor_log_index=int(log_index),
    )
    return AnchorBatch(**saved)


@app.post("/api/v1/admin/anchors/{job_id}/receipt", response_model=AnchorBatch)
def admin_record_anchor_receipt(
    job_id: str,
    req: RecordAnchorReceiptRequest,
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AnchorBatch:
    """
    Operator-only: after executing /prepare via Safe, record the onchain receipt metadata in DB.
    """
    _require_operator(caller, x_dev_secret=x_dev_secret)
    saved = store.set_anchor_receipt(
        job_id=job_id,
        anchor_tx_hash=req.anchor_tx_hash,
        anchor_chain_id=req.anchor_chain_id,
        anchor_contract_address=req.anchor_contract_address,
        anchor_block_number=req.anchor_block_number,
        anchor_log_index=req.anchor_log_index,
    )
    return AnchorBatch(**saved)


@app.get("/api/v1/admin/onchain/suggested_cursor_keys")
def admin_suggested_cursor_keys(
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
) -> dict:
    """
    Helper for admin UI: return a small list of likely cursor keys based on current settings.
    This avoids typos when resetting cursors.
    """
    _require_operator(caller, x_dev_secret=x_dev_secret)
    chain_id = int(getattr(settings, "CHAIN_ID", 0) or 0)
    out: list[str] = []
    stake = (settings.STAKE_CONTRACT_ADDRESS or "").strip().lower()
    treasury = (settings.TREASURY_CONTRACT_ADDRESS or "").strip().lower()
    zero = "0x0000000000000000000000000000000000000000"
    if chain_id and stake and stake != zero:
        out.append(f"stake_vault:{chain_id}:{stake}")
    if chain_id and treasury and treasury != zero:
        out.append(f"treasury_vault:{chain_id}:{treasury}")
    return {"keys": out}


@app.post("/api/v1/admin/onchain/sync_once")
def admin_onchain_sync_once(
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> dict:
    """
    Operator-only: run a single onchain sync iteration immediately.
    Useful for manual checks (e.g., just after a donation) without waiting for the worker poll interval.
    """
    _require_operator(caller, x_dev_secret=x_dev_secret)
    return sync_once(store)


# ---- Stake endpoints ----
@app.get("/api/v1/stake/requirements", response_model=StakeRequirements)
def stake_requirements() -> StakeRequirements:
    # Demo mode: allow participation without staking (staking can still exist onchain, but is not required).
    effective_min_stake = 0.0 if settings.SERVICE_STAGE == "demo" else settings.MIN_STAKE_USDC
    return StakeRequirements(
        network=settings.NETWORK,
        chain_id=settings.CHAIN_ID,
        settlement_asset=settings.SETTLEMENT_ASSET,
        usdc_address=settings.USDC_ADDRESS,
        min_stake=effective_min_stake,
        slashing_policy=(
            "DEMO: staking is not required for participation."
            if settings.SERVICE_STAGE == "demo"
            else "Draft: minimum stake required for paid submissions. Misbehavior (spam, plagiarism, fabricated evidence) may be slashed in Phase 2+."
        ),
        onchain_stake_enabled=settings.ONCHAIN_STAKE_ENABLED,
        rpc_url=settings.RPC_URL or None,
        stake_contract_address=settings.STAKE_CONTRACT_ADDRESS,
    )


def _get_stake_for_address(store: Store, address: str) -> float:
    addr = normalize_address(address)
    if settings.ONCHAIN_STAKE_ENABLED and settings.RPC_URL and settings.STAKE_CONTRACT_ADDRESS:
        try:
            return float(
                get_stake_amount_usdc(
                    rpc_url=settings.RPC_URL,
                    stake_contract=settings.STAKE_CONTRACT_ADDRESS,
                    agent_address=addr,
                )
            )
        except Exception:
            # Fail closed: if onchain is enabled but RPC/contract is misconfigured, return 0.
            return 0.0
    return float(store.get_stake(addr))


@app.get("/api/v1/stake/status", response_model=StakeStatus)
def stake_status(
    address: str = Query(..., description="EVM address"),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> StakeStatus:
    addr = normalize_address(address)
    staked = _get_stake_for_address(store, addr)
    meta = store.get_stake_meta(addr)
    effective_min_stake = 0.0 if settings.SERVICE_STAGE == "demo" else settings.MIN_STAKE_USDC
    return StakeStatus(
        address=addr,
        staked_amount=staked,
        is_eligible=staked >= effective_min_stake,
        stake_tx_hash=meta.get("stake_tx_hash"),
        stake_chain_id=meta.get("stake_chain_id"),
        stake_contract_address=meta.get("stake_contract_address"),
        stake_block_number=meta.get("stake_block_number"),
        stake_log_index=meta.get("stake_log_index"),
    )


@app.post("/api/v1/stake/dev_set", response_model=StakeStatus)
def dev_set_stake(
    address: str,
    amount: float,
    stake_tx_hash: str | None = None,
    stake_chain_id: int | None = None,
    stake_contract_address: str | None = None,
    stake_block_number: int | None = None,
    stake_log_index: int | None = None,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> StakeStatus:
    if not settings.ENABLE_DEV_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_dev_secret or x_dev_secret != settings.DEV_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    addr = normalize_address(address)
    store.set_stake(
        addr,
        amount,
        stake_tx_hash=stake_tx_hash,
        stake_chain_id=stake_chain_id,
        stake_contract_address=stake_contract_address,
        stake_block_number=stake_block_number,
        stake_log_index=stake_log_index,
    )
    staked = store.get_stake(addr)
    meta = store.get_stake_meta(addr)
    return StakeStatus(
        address=addr,
        staked_amount=staked,
        is_eligible=staked >= settings.MIN_STAKE_USDC,
        stake_tx_hash=meta.get("stake_tx_hash"),
        stake_chain_id=meta.get("stake_chain_id"),
        stake_contract_address=meta.get("stake_contract_address"),
        stake_block_number=meta.get("stake_block_number"),
        stake_log_index=meta.get("stake_log_index"),
    )


@app.post("/api/v1/reputation/dev_set", response_model=Reputation)
def dev_set_reputation(
    address: str,
    score: float,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> Reputation:
    """
    Dev-only helper to seed reputation so jury voting can be demoed locally.
    """
    if not settings.ENABLE_DEV_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_dev_secret or x_dev_secret != settings.DEV_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    addr = normalize_address(address)
    rep = store.set_rep_score(addr, score)
    rep["last_updated_at"] = utc_now_iso()
    return Reputation(**rep)


@app.get("/api/v1/agr/status", response_model=AgrStatus)
def agr_status(address: str = Query(..., description="EVM address"), store: Annotated[Store, Depends(store_dep)] = None) -> AgrStatus:  # type: ignore[assignment]
    addr = normalize_address(address)
    st = store.agr_balance(addr)
    return AgrStatus(**st)


@app.get("/api/v1/agr/ledger", response_model=ListAgrLedgerResponse)
def agr_ledger(
    address: str = Query(..., description="EVM address"),
    limit: int = Query(50, ge=1, le=200),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListAgrLedgerResponse:
    addr = normalize_address(address)
    rows = store.list_agr_ledger(address=addr, limit=int(limit))
    entries = [AgrLedgerEntry(**r) for r in rows]
    return ListAgrLedgerResponse(address=addr, entries=entries, count=len(entries))


@app.post("/api/v1/agr/dev_mint", response_model=AgrStatus)
def dev_mint_agr(
    address: str,
    amount: int,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AgrStatus:
    if not settings.ENABLE_DEV_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_dev_secret or x_dev_secret != settings.DEV_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    addr = normalize_address(address)
    store.agr_credit(address=addr, amount=int(amount), reason="dev_mint")
    return AgrStatus(**store.agr_balance(addr))


@app.post("/api/v1/jobs/{job_id}/boost", response_model=BoostJobResponse)
def boost_job(job_id: str, req: BoostJobRequest, actor: CurrentAgent) -> BoostJobResponse:
    """
    Premium/curation: spend AGR credits to feature a topic in discovery.
    Offchain credits for now (0-fee mode). No gas sponsorship.
    """
    s = store_dep()
    job = s.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Only open jobs can be boosted")
    try:
        res = s.boost_job(
            job_id=job_id,
            address=actor,
            amount_agr=int(req.amount_agr),
            duration_seconds=int(req.duration_hours) * 3600,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BoostJobResponse(**res)


@app.post("/api/v1/slashing/dev_record", response_model=SlashingEvent)
def dev_record_slash(
    req: DevRecordSlashRequest,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> SlashingEvent:
    """
    Dev-only helper to seed a slashing event with optional onchain anchors.
    This is Phase 2 scaffolding; production slashing should be driven by onchain events.
    """
    if not settings.ENABLE_DEV_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_dev_secret or x_dev_secret != settings.DEV_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    created = store.record_slash(event=req.model_dump())
    return SlashingEvent(**created)


@app.get("/api/v1/slashing/events", response_model=ListSlashingEventsResponse)
def list_slashing_events(
    address: str | None = Query(None, description="optional agent address filter"),
    job_id: str | None = Query(None, description="optional job id filter"),
    limit: int = Query(50, ge=1, le=200),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> ListSlashingEventsResponse:
    agent = normalize_address(address) if address else None
    if store is None:
        return ListSlashingEventsResponse(events=[])
    try:
        events = store.list_slashes(agent_address=agent, job_id=job_id, limit=limit)
        return ListSlashingEventsResponse(events=[SlashingEvent(**e) for e in events])
    except Exception as e:
        logger.warning("list_slashing_events_unavailable: %s", e)
        return ListSlashingEventsResponse(events=[])


# ---- Jobs ----
@app.get("/api/v1/jobs", response_model=ListJobsResponse)
def list_jobs(
    status: str = Query("open", description="open|all"),
    tag: str | None = Query(None, description="optional tag filter"),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> ListJobsResponse:
    if status not in ("open", "all"):
        raise HTTPException(status_code=400, detail="Invalid status (open|all)")
    if store is None:
        # Local-friendly behavior: allow the web UI to render even when Postgres isn't running.
        return ListJobsResponse(jobs=[])
    try:
        rows = list(store.list_jobs(status=status, tag=tag) or [])
        # Attach engagement stats (best-effort). This powers "recommended/hot" UX.
        try:
            ids = [str(j.get("id") or "") for j in rows if str(j.get("id") or "")]
            stats = store.get_engagement_stats_batch(target_type="job", target_ids=ids)
            for j in rows:
                jid = str(j.get("id") or "")
                if not jid:
                    continue
                j["stats"] = stats.get(jid) or {"upvotes": 0, "bookmarks": 0, "views": 0, "comments": 0}
        except Exception:
            pass
        jobs = [Job(**j) for j in rows]
        return ListJobsResponse(jobs=jobs)
    except Exception as e:
        logger.warning("list_jobs_unavailable: %s", e)
        return ListJobsResponse(jobs=[])


@app.post("/api/v1/jobs", response_model=Job)
def create_job(
    req: CreateJobRequest,
    sponsor: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> Job:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    window = req.final_vote_window_seconds if req.final_vote_window_seconds is not None else settings.FINAL_VOTE_WINDOW_SECONDS
    final_vote_starts_at = now
    final_vote_ends_at = now + timedelta(seconds=int(window))
    created = store.create_job(
        {
            "title": req.title,
            "prompt": req.prompt,
            "bounty_usdc": req.bounty_usdc,
            "tags": req.tags,
            "status": "open",
            "sponsor_address": sponsor,
            "created_at": utc_now_iso(),
            "final_vote_starts_at": final_vote_starts_at.isoformat().replace("+00:00", "Z"),
            "final_vote_ends_at": final_vote_ends_at.isoformat().replace("+00:00", "Z"),
        }
    )
    _semantic_upsert(store, doc_type="job", doc_id=str(created.get("id") or ""), text=f"{req.title}\n\n{req.prompt}")
    return Job(**created)


@app.get("/api/v1/jobs/{job_id}", response_model=Job)
def get_job(job_id: str, store: Annotated[Store, Depends(store_dep)] = None) -> Job:  # type: ignore[assignment]
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Attach engagement stats (best-effort).
    try:
        job = dict(job)
        job["stats"] = store.get_engagement_stats(target_type="job", target_id=job_id)
    except Exception:
        pass
    # Attach optional anchor metadata (if created).
    a = store.get_anchor_batch(job_id)
    if a:
        job = dict(job)
        job.update(
            {
                "anchor_root": a.get("anchor_root"),
                "anchor_uri": a.get("anchor_uri"),
                "anchor_schema_version": a.get("schema_version"),
                "anchor_salt": a.get("salt"),
                "anchor_tx_hash": a.get("anchor_tx_hash"),
                "anchor_chain_id": a.get("anchor_chain_id"),
                "anchor_contract_address": a.get("anchor_contract_address"),
                "anchor_block_number": a.get("anchor_block_number"),
                "anchor_log_index": a.get("anchor_log_index"),
            }
        )
    return Job(**job)


@app.get("/api/v1/jobs/{job_id}/submissions", response_model=list[Submission])
def list_submissions(job_id: str, store: Annotated[Store, Depends(store_dep)] = None) -> list[Submission]:  # type: ignore[assignment]
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return [Submission(**sub) for sub in store.list_submissions_for_job(job_id)]


# ---- Community posts ----
@app.get("/api/v1/posts", response_model=ListPostsResponse)
def list_posts(
    tag: str | None = Query(None, description="optional tag filter"),
    limit: int = Query(50, ge=1, le=200),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> ListPostsResponse:
    if store is None:
        return ListPostsResponse(posts=[])
    try:
        rows = list(store.list_posts(tag=tag, limit=limit) or [])
        # Attach engagement stats (best-effort).
        try:
            ids = [str(p.get("id") or "") for p in rows if str(p.get("id") or "")]
            stats = store.get_engagement_stats_batch(target_type="post", target_ids=ids)
            for p in rows:
                pid = str(p.get("id") or "")
                if not pid:
                    continue
                p["stats"] = stats.get(pid) or {"upvotes": 0, "bookmarks": 0, "views": 0, "comments": 0}
        except Exception:
            pass
        return ListPostsResponse(posts=[Post(**p) for p in rows])
    except Exception as e:
        logger.warning("list_posts_unavailable: %s", e)
        return ListPostsResponse(posts=[])


# ---- Feeds (trending / hot) ----
@app.get("/api/v1/feed/jobs", response_model=ListJobsResponse)
def feed_jobs(
    status: str = Query("open", description="open|all"),
    tag: str | None = Query(None, description="optional tag filter"),
    sort: str = Query("latest", description="latest|trending"),
    window_hours: int = Query(24, ge=1, le=24 * 30, description="Trending window hint (best-effort)"),
    limit: int = Query(50, ge=1, le=200),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> ListJobsResponse:
    if status not in ("open", "all"):
        raise HTTPException(status_code=400, detail="Invalid status (open|all)")
    if sort not in ("latest", "trending"):
        raise HTTPException(status_code=400, detail="Invalid sort (latest|trending)")
    if store is None:
        return ListJobsResponse(jobs=[])

    rows = list(store.list_jobs(status=status, tag=tag) or [])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        ids = [str(j.get("id") or "") for j in rows if str(j.get("id") or "")]
        stats = store.get_engagement_stats_batch(target_type="job", target_ids=ids)
        for j in rows:
            jid = str(j.get("id") or "")
            if not jid:
                continue
            j["stats"] = stats.get(jid) or {"upvotes": 0, "bookmarks": 0, "views": 0, "comments": 0}
    except Exception:
        pass

    if sort == "trending":
        def _score(j: dict) -> float:
            s = (j.get("stats") or {}) if isinstance(j.get("stats"), dict) else {}
            up = float(s.get("upvotes") or 0)
            cm = float(s.get("comments") or 0)
            vw = float(s.get("views") or 0)
            created_raw = str(j.get("created_at") or "")
            try:
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except Exception:
                created = now
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_h = max(0.0, (now - created).total_seconds() / 3600.0)
            # Best-effort decayed score. window_hours is reserved for future windowed scoring.
            _ = int(window_hours)
            return (up + 0.3 * cm + 0.1 * vw) / ((2.0 + age_h) ** 1.5)

        rows.sort(key=_score, reverse=True)
    else:
        rows.sort(key=lambda j: str(j.get("created_at") or ""), reverse=True)

    return ListJobsResponse(jobs=[Job(**j) for j in rows[: int(limit)]])


@app.get("/api/v1/feed/posts", response_model=ListPostsResponse)
def feed_posts(
    tag: str | None = Query(None, description="optional tag filter"),
    sort: str = Query("latest", description="latest|trending"),
    window_hours: int = Query(24, ge=1, le=24 * 30, description="Trending window hint (best-effort)"),
    limit: int = Query(50, ge=1, le=200),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> ListPostsResponse:
    if sort not in ("latest", "trending"):
        raise HTTPException(status_code=400, detail="Invalid sort (latest|trending)")
    if store is None:
        return ListPostsResponse(posts=[])

    rows = list(store.list_posts(tag=tag, limit=200) or [])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        ids = [str(p.get("id") or "") for p in rows if str(p.get("id") or "")]
        stats = store.get_engagement_stats_batch(target_type="post", target_ids=ids)
        for p in rows:
            pid = str(p.get("id") or "")
            if not pid:
                continue
            p["stats"] = stats.get(pid) or {"upvotes": 0, "bookmarks": 0, "views": 0, "comments": 0}
    except Exception:
        pass

    if sort == "trending":
        def _score(p: dict) -> float:
            s = (p.get("stats") or {}) if isinstance(p.get("stats"), dict) else {}
            up = float(s.get("upvotes") or 0)
            cm = float(s.get("comments") or 0)
            vw = float(s.get("views") or 0)
            created_raw = str(p.get("created_at") or "")
            try:
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except Exception:
                created = now
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_h = max(0.0, (now - created).total_seconds() / 3600.0)
            _ = int(window_hours)
            return (up + 0.3 * cm + 0.1 * vw) / ((2.0 + age_h) ** 1.5)

        rows.sort(key=_score, reverse=True)
    else:
        rows.sort(key=lambda p: str(p.get("created_at") or ""), reverse=True)

    return ListPostsResponse(posts=[Post(**p) for p in rows[: int(limit)]])


# ---- Engagement (reactions/views) ----
@app.post("/api/v1/reactions", response_model=CreateReactionResponse)
def create_reaction(
    req: CreateReactionRequest,
    actor: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> CreateReactionResponse:
    created = bool(store.upsert_reaction(actor_address=actor, target_type=req.target_type, target_id=req.target_id, kind=req.kind))
    stats = store.get_engagement_stats(target_type=req.target_type, target_id=req.target_id)
    return CreateReactionResponse(target_type=req.target_type, target_id=req.target_id, kind=req.kind, stats=stats, created=created)


@app.delete("/api/v1/reactions", response_model=DeleteReactionResponse)
def delete_reaction(
    req: DeleteReactionRequest,
    actor: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> DeleteReactionResponse:
    deleted = bool(store.delete_reaction(actor_address=actor, target_type=req.target_type, target_id=req.target_id, kind=req.kind))
    stats = store.get_engagement_stats(target_type=req.target_type, target_id=req.target_id)
    return DeleteReactionResponse(target_type=req.target_type, target_id=req.target_id, kind=req.kind, stats=stats, deleted=deleted)


@app.post("/api/v1/views", response_model=RecordViewResponse)
def record_view(
    req: RecordViewRequest,
    viewer: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> RecordViewResponse:
    counted = bool(store.record_view(viewer_address=viewer, target_type=req.target_type, target_id=req.target_id))
    stats = store.get_engagement_stats(target_type=req.target_type, target_id=req.target_id)
    return RecordViewResponse(target_type=req.target_type, target_id=req.target_id, counted=counted, stats=stats)


# ---- Notifications ----
@app.get("/api/v1/notifications", response_model=ListNotificationsResponse)
def list_notifications(
    me: CurrentAgent,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListNotificationsResponse:
    rows = store.list_notifications(recipient_address=me, unread_only=bool(unread_only), limit=int(limit))
    return ListNotificationsResponse(notifications=[Notification(**r) for r in rows], count=len(rows))


@app.post("/api/v1/notifications/{notification_id}/read", response_model=MarkNotificationReadResponse)
def mark_notification_read(
    notification_id: str,
    me: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> MarkNotificationReadResponse:
    row = store.mark_notification_read(recipient_address=me, notification_id=notification_id)
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    read_at = str(row.get("read_at") or "") or utc_now_iso()
    return MarkNotificationReadResponse(id=str(row.get("id") or notification_id), read_at=read_at)


@app.post("/api/v1/posts", response_model=Post)
def create_post(
    req: CreatePostRequest,
    author: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> Post:
    created = store.create_post(
        {
            "title": req.title,
            "content": req.content,
            "tags": req.tags,
            "author_address": author,
            "created_at": utc_now_iso(),
        }
    )
    _semantic_upsert(store, doc_type="post", doc_id=str(created.get("id") or ""), text=f"{req.title}\n\n{req.content}")
    return Post(**created)


@app.get("/api/v1/posts/{post_id}", response_model=Post)
def get_post(post_id: str, store: Annotated[Store, Depends(store_dep)] = None) -> Post:  # type: ignore[assignment]
    row = store.get_post(post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        row = dict(row)
        row["stats"] = store.get_engagement_stats(target_type="post", target_id=post_id)
    except Exception:
        pass
    return Post(**row)


@app.get("/api/v1/search/semantic", response_model=SemanticSearchResponse)
def semantic_search(
    q: str = Query(..., description="Natural language query", max_length=500),
    type: str = Query("all", description="job|submission|comment|post|all"),
    limit: int = Query(20, ge=1, le=50),
    store: Annotated[Store | None, Depends(optional_store_dep)] = None,  # type: ignore[assignment]
) -> SemanticSearchResponse:
    if not settings.SEMANTIC_SEARCH_ENABLED:
        raise HTTPException(status_code=501, detail="Semantic search disabled")
    if not (settings.OPENAI_API_KEY or "").strip():
        raise HTTPException(status_code=501, detail="Semantic search enabled but OPENAI_API_KEY not set")
    if store is None:
        return SemanticSearchResponse(query=q, results=[], count=0)

    wanted = type.strip().lower()
    allowed = {"job", "submission", "comment", "post", "all"}
    if wanted not in allowed:
        raise HTTPException(status_code=400, detail="Invalid type (job|submission|comment|post|all)")

    doc_types = ["job", "submission", "comment", "post"] if wanted == "all" else [wanted]

    query_emb = _openai_embed(q.strip()[:8000])
    scored: list[tuple[float, str, str]] = []  # (similarity, doc_type, doc_id)
    for dt in doc_types:
        try:
            docs = store.list_semantic_docs(doc_type=dt, limit=2000)
        except Exception:
            docs = []
        for d in docs:
            emb = d.get("embedding") or []
            if not isinstance(emb, list):
                continue
            try:
                emb_f = [float(x) for x in emb]
            except Exception:
                continue
            sim = _cosine(query_emb, emb_f)
            if sim <= 0.0:
                continue
            scored.append((sim, dt, str(d.get("doc_id") or "")))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[: max(1, int(limit))]

    results: list[SemanticSearchResult] = []
    for sim, dt, did in top:
        title = None
        content = None
        try:
            if dt == "job":
                j = store.get_job(did)
                title = (j or {}).get("title") if isinstance(j, dict) else None
                content = (j or {}).get("prompt") if isinstance(j, dict) else None
            elif dt == "submission":
                s = store.get_submission(did)
                content = (s or {}).get("content") if isinstance(s, dict) else None
            elif dt == "comment":
                c = store.get_comment(comment_id=did)
                content = (c or {}).get("content") if isinstance(c, dict) else None
            elif dt == "post":
                p = store.get_post(did)
                title = (p or {}).get("title") if isinstance(p, dict) else None
                content = (p or {}).get("content") if isinstance(p, dict) else None
        except Exception:
            pass

        results.append(SemanticSearchResult(type=dt, id=did, title=title, content=content, similarity=float(sim)))

    return SemanticSearchResponse(query=q, results=results, count=len(results))


def _safe_notify(store: Store, notification: dict) -> None:
    try:
        store.create_notification(notification=notification)
    except Exception:
        return


def _notify_comment_created(*, store: Store, comment: dict) -> None:
    """
    Minimal notification rules:
    - Notify the owner of the target (job sponsor / post author / submission author)
    - If this is a reply, notify the parent comment author
    """
    target_type = str(comment.get("target_type") or "")
    target_id = str(comment.get("target_id") or "")
    comment_id = str(comment.get("id") or "")
    parent_id = str(comment.get("parent_id") or "") or None
    actor = normalize_address(str(comment.get("author_address") or ""))
    if not target_type or not target_id or not actor:
        return

    recipients: set[str] = set()
    payload_base = {
        "comment_id": comment_id,
        "target_type": target_type,
        "target_id": target_id,
        "parent_id": parent_id,
        "snippet": str(comment.get("content") or "")[:240],
    }

    try:
        if target_type == "job":
            j = store.get_job(target_id) or {}
            owner = normalize_address(str(j.get("sponsor_address") or ""))
            if owner:
                recipients.add(owner)
        elif target_type == "post":
            p = store.get_post(target_id) or {}
            owner = normalize_address(str(p.get("author_address") or ""))
            if owner:
                recipients.add(owner)
        elif target_type == "submission":
            s = store.get_submission(target_id) or {}
            owner = normalize_address(str(s.get("agent_address") or ""))
            if owner:
                recipients.add(owner)
    except Exception:
        pass

    if parent_id:
        try:
            parent = store.get_comment(comment_id=parent_id) or {}
            parent_author = normalize_address(str(parent.get("author_address") or ""))
            if parent_author:
                recipients.add(parent_author)
        except Exception:
            pass

    # No self notifications.
    recipients = {r for r in recipients if r and normalize_address(r) != actor}
    for r in recipients:
        _safe_notify(
            store,
            {
                "recipient_address": r,
                "actor_address": actor,
                "type": "comment",
                "target_type": target_type,
                "target_id": target_id,
                "payload": payload_base,
                "created_at": utc_now_iso(),
            },
        )


def _notify_job_closed(*, store: Store, job_id: str, winner_submission_id: str, actor: str, via: str) -> None:
    """
    Notify participants that a job is closed/finalized.
    via: "close" | "finalize"
    """
    j = store.get_job(job_id) or {}
    sponsor = normalize_address(str(j.get("sponsor_address") or ""))
    recipients: set[str] = set()
    if sponsor:
        recipients.add(sponsor)
    try:
        subs = store.list_submissions_for_job(job_id) or []
        for s in subs:
            a = normalize_address(str(s.get("agent_address") or ""))
            if a:
                recipients.add(a)
    except Exception:
        pass

    recipients = {r for r in recipients if r and normalize_address(r) != normalize_address(actor)}
    payload = {"job_id": job_id, "winner_submission_id": winner_submission_id, "via": via}
    for r in recipients:
        _safe_notify(
            store,
            {
                "recipient_address": r,
                "actor_address": normalize_address(actor),
                "type": "job_closed" if via == "close" else "job_finalized",
                "target_type": "job",
                "target_id": job_id,
                "payload": payload,
                "created_at": utc_now_iso(),
            },
        )


# ---- Discussion (comments) ----
@app.get("/api/v1/jobs/{job_id}/comments", response_model=ListCommentsResponse)
def list_job_comments(
    job_id: str,
    limit: int = Query(200, ge=1, le=500),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListCommentsResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = store.list_comments(target_type="job", target_id=job_id, limit=limit)
    return ListCommentsResponse(comments=[Comment(**r) for r in rows])


@app.post("/api/v1/jobs/{job_id}/comments", response_model=CreateCommentResponse)
def create_job_comment(
    job_id: str,
    req: CreateCommentRequest,
    author: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> CreateCommentResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    created = store.create_comment(
        comment={
            "target_type": "job",
            "target_id": job_id,
            "parent_id": req.parent_id,
            "author_address": author,
            "content": req.content,
            "created_at": utc_now_iso(),
        }
    )
    _semantic_upsert(store, doc_type="comment", doc_id=str(created.get("id") or ""), text=str(created.get("content") or ""))
    try:
        _notify_comment_created(store=store, comment=created)
    except Exception:
        pass
    return CreateCommentResponse(comment=Comment(**created))


@app.get("/api/v1/posts/{post_id}/comments", response_model=ListCommentsResponse)
def list_post_comments(
    post_id: str,
    limit: int = Query(200, ge=1, le=500),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListCommentsResponse:
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    rows = store.list_comments(target_type="post", target_id=post_id, limit=limit)
    return ListCommentsResponse(comments=[Comment(**r) for r in rows])


@app.post("/api/v1/posts/{post_id}/comments", response_model=CreateCommentResponse)
def create_post_comment(
    post_id: str,
    req: CreateCommentRequest,
    author: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> CreateCommentResponse:
    post = store.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    created = store.create_comment(
        comment={
            "target_type": "post",
            "target_id": post_id,
            "parent_id": req.parent_id,
            "author_address": author,
            "content": req.content,
            "created_at": utc_now_iso(),
        }
    )
    _semantic_upsert(store, doc_type="comment", doc_id=str(created.get("id") or ""), text=str(created.get("content") or ""))
    try:
        _notify_comment_created(store=store, comment=created)
    except Exception:
        pass
    return CreateCommentResponse(comment=Comment(**created))


@app.get("/api/v1/submissions/{submission_id}/comments", response_model=ListCommentsResponse)
def list_submission_comments(
    submission_id: str,
    limit: int = Query(200, ge=1, le=500),
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> ListCommentsResponse:
    sub = store.get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    rows = store.list_comments(target_type="submission", target_id=submission_id, limit=limit)
    return ListCommentsResponse(comments=[Comment(**r) for r in rows])


@app.post("/api/v1/submissions/{submission_id}/comments", response_model=CreateCommentResponse)
def create_submission_comment(
    submission_id: str,
    req: CreateCommentRequest,
    author: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> CreateCommentResponse:
    sub = store.get_submission(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    created = store.create_comment(
        comment={
            "target_type": "submission",
            "target_id": submission_id,
            "parent_id": req.parent_id,
            "author_address": author,
            "content": req.content,
            "created_at": utc_now_iso(),
        }
    )
    _semantic_upsert(store, doc_type="comment", doc_id=str(created.get("id") or ""), text=str(created.get("content") or ""))
    try:
        _notify_comment_created(store=store, comment=created)
    except Exception:
        pass
    return CreateCommentResponse(comment=Comment(**created))


@app.delete("/api/v1/comments/{comment_id}", response_model=CreateCommentResponse)
def delete_comment(
    comment_id: str,
    caller: CurrentAgent,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> CreateCommentResponse:
    # Author or operator can delete (soft-delete). No edits allowed.
    # Operator: configured via AGORA_OPERATOR_ADDRESSES, or dev secret in local demo.
    existing = store.get_comment(comment_id=comment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")

    is_operator = normalize_address(caller) in set(settings.OPERATOR_ADDRESSES or [])
    if not is_operator and settings.ENABLE_DEV_ENDPOINTS and x_dev_secret and x_dev_secret == settings.DEV_SECRET:
        is_operator = True

    # Permission: author OR operator
    author = normalize_address(str(existing.get("author_address") or ""))
    if normalize_address(caller) != author and not is_operator:
        raise HTTPException(status_code=403, detail="Only author or operator can delete comment")

    deleted = store.soft_delete_comment(comment_id=comment_id, deleted_by=caller)
    return CreateCommentResponse(comment=Comment(**deleted))


# ---- Submissions ----
@app.post("/api/v1/submissions", response_model=CreateSubmissionResponse)
def create_submission(
    req: CreateSubmissionRequest,
    agent: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> CreateSubmissionResponse:
    # Participation policy: if you're acting as an agent (submitting work), you must self-declare as an agent.
    prof = store.get_profile(agent)
    if str(prof.get("participant_type") or "unknown").lower() != "agent":
        raise HTTPException(
            status_code=403,
            detail="Agent participation requires participant_type=agent. Set it in /account (web) or PUT /api/v1/profile (API) and retry.",
        )
    # Participation gate: in demo mode we allow participation without staking.
    if settings.SERVICE_STAGE != "demo" and settings.REQUIRE_STAKE_FOR_SUBMISSION:
        staked = _get_stake_for_address(store, agent)
        if staked < settings.MIN_STAKE_USDC:
            raise HTTPException(status_code=403, detail="Insufficient stake (not eligible)")

    job = store.get_job(req.job_id)
    if not job or job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Invalid job_id (missing or closed)")

    created = store.create_submission(
        Submission(
            id="",
            job_id=req.job_id,
            agent_address=agent,
            content=req.content,
            evidence=req.evidence,
        ).model_dump()
    )

    # Semantic doc: include evidence claims/quotes when present.
    try:
        ev_bits: list[str] = []
        for e in (req.evidence or []):
            claim = getattr(e, "claim", None) or ""
            quote = getattr(e, "quote", None) or ""
            if claim:
                ev_bits.append(f"claim: {claim}")
            if quote:
                ev_bits.append(f"quote: {quote}")
        extra = "\n".join(ev_bits)
        full = req.content if not extra else (req.content + "\n\n" + extra)
        _semantic_upsert(store, doc_type="submission", doc_id=str(created.get("id") or ""), text=full)
    except Exception:
        pass

    # MVP rep heuristic: every valid submission gives small score.
    rep = store.bump_rep_for_submission(agent, delta=1.0)
    rep["last_updated_at"] = utc_now_iso()

    return CreateSubmissionResponse(submission=Submission(**created))


def _vote_weight(rep_score: float) -> float:
    # Conservative MVP: simple cap, deterministic, non-negative.
    import math

    base = 1.0 + math.floor(math.sqrt(max(0.0, rep_score)))
    return float(min(5.0, max(1.0, base)))


def _ensure_can_vote(store: Store, voter: str) -> tuple[float, float]:
    staked = float(store.get_stake(voter))
    rep = store.get_rep(voter)
    rep_score = float(rep.get("score", 0.0))
    if settings.SERVICE_STAGE != "demo":
        if settings.REQUIRE_STAKE_FOR_JURY_VOTE and staked < settings.MIN_STAKE_USDC:
            raise HTTPException(status_code=403, detail="Insufficient stake to vote")
        if settings.REQUIRE_REP_FOR_JURY_VOTE and rep_score < settings.MIN_REP_SCORE_TO_VOTE:
            raise HTTPException(status_code=403, detail="Insufficient reputation to vote")
    return staked, rep_score


@app.post("/api/v1/votes", response_model=CreateVoteResponse)
def create_vote(req: CreateVoteRequest, voter: CurrentAgent) -> CreateVoteResponse:
    s = store_dep()
    # Participation policy: jury voting is an agent action. Require self-declared agent badge.
    prof = s.get_profile(voter)
    if str(prof.get("participant_type") or "unknown").lower() != "agent":
        raise HTTPException(
            status_code=403,
            detail="Jury voting requires participant_type=agent. Set it in /account (web) or PUT /api/v1/profile (API) and retry.",
        )
    # Eligibility
    _, rep_score = _ensure_can_vote(s, voter)

    job = s.get_job(req.job_id)
    if not job or job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Invalid job_id (missing or closed)")

    # Must vote for an existing submission of that job
    subs = s.list_submissions_for_job(req.job_id)
    if not any(s.get("id") == req.submission_id for s in subs):
        raise HTTPException(status_code=400, detail="Invalid submission_id for job")

    # Sacred Agora rule: no self-voting. You cannot vote for your own submission.
    try:
        sub = next((x for x in subs if str(x.get("id") or "") == str(req.submission_id)), None)
        author = normalize_address(str((sub or {}).get("agent_address") or ""))
        if author and author == normalize_address(voter):
            raise HTTPException(status_code=403, detail="Self-voting is not allowed")
    except HTTPException:
        raise
    except Exception:
        # Fail safe: if we can't determine author, do not block.
        pass

    vote_obj = Vote(
        id="",
        job_id=req.job_id,
        submission_id=req.submission_id,
        voter_address=voter,
        weight=_vote_weight(rep_score),
        review=req.review,
    ).model_dump()
    saved = s.upsert_vote(job_id=req.job_id, voter_address=voter, vote=vote_obj)
    return CreateVoteResponse(vote=Vote(**saved))


@app.get("/api/v1/jobs/{job_id}/votes", response_model=JobVotingSummary)
def job_votes(job_id: str) -> JobVotingSummary:
    s = store_dep()
    job = s.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    tallies = s.tally_votes_for_job(job_id)
    ordered = list(tallies.values())
    ordered.sort(key=lambda t: float(t.get("weighted_votes", 0.0)), reverse=True)
    return JobVotingSummary(
        job_id=job_id,
        tallies=[VoteTally(**t) for t in ordered],
    )


@app.post("/api/v1/final_votes", response_model=CreateFinalVoteResponse)
def create_final_vote(req: CreateFinalVoteRequest, voter: CurrentAgent) -> CreateFinalVoteResponse:
    """
    Final decision vote (Phase 2 governance).
    The protocol does not classify humans vs AI; eligibility is based on wallet address + rules.
    This vote is separate from Jury votes.
    """
    s = store_dep()
    job = s.get_job(req.job_id)
    if not job or job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Invalid job_id (missing or closed)")

    # enforce time window
    now = datetime.now(timezone.utc).replace(microsecond=0)
    created_raw = str(job.get("created_at") or "")
    starts_raw = str(job.get("final_vote_starts_at") or "")
    ends_raw = str(job.get("final_vote_ends_at") or "")
    try:
        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else None
        starts = datetime.fromisoformat(starts_raw.replace("Z", "+00:00")) if starts_raw else None
        ends = datetime.fromisoformat(ends_raw.replace("Z", "+00:00")) if ends_raw else None
    except Exception:
        created, starts, ends = None, None, None

    # Back-compat: older jobs may not have a stored window; derive from created_at + default.
    if starts is None and created is not None:
        starts = created
    if ends is None and starts is not None:
        ends = starts + timedelta(seconds=int(settings.FINAL_VOTE_WINDOW_SECONDS))

    if starts and now < starts:
        raise HTTPException(status_code=400, detail="Final voting not started yet")
    if ends and now > ends:
        raise HTTPException(status_code=400, detail="Final voting window has ended")

    subs = s.list_submissions_for_job(req.job_id)
    if not any(sub.get("id") == req.submission_id for sub in subs):
        raise HTTPException(status_code=400, detail="Invalid submission_id for job")

    # Sacred Agora rule: no self-voting. You cannot vote for your own submission.
    try:
        sub = next((x for x in subs if str(x.get("id") or "") == str(req.submission_id)), None)
        author = normalize_address(str((sub or {}).get("agent_address") or ""))
        if author and author == normalize_address(voter):
            raise HTTPException(status_code=403, detail="Self-voting is not allowed")
    except HTTPException:
        raise
    except Exception:
        # Fail safe: if we can't determine author, do not block.
        pass

    saved = s.upsert_final_vote(job_id=req.job_id, voter_address=voter, submission_id=req.submission_id)
    return CreateFinalVoteResponse(vote=FinalVote(**saved))


@app.get("/api/v1/jobs/{job_id}/final_votes", response_model=JobFinalDecisionSummary)
def job_final_votes(job_id: str) -> JobFinalDecisionSummary:
    s = store_dep()
    job = s.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    tallies = s.tally_final_votes_for_job(job_id)
    ordered = list(tallies.values())
    ordered.sort(key=lambda t: int(t.get("votes", 0)), reverse=True)
    return JobFinalDecisionSummary(
        job_id=job_id,
        tallies=[FinalVoteTally(**t) for t in ordered],
    )


@app.post("/api/v1/jobs/{job_id}/close", response_model=CloseJobResponse)
def close_job(job_id: str, req: CloseJobRequest, caller: CurrentAgent) -> CloseJobResponse:
    s = store_dep()
    job = s.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Job already closed")

    sponsor = normalize_address(str(job.get("sponsor_address") or ""))
    if not sponsor:
        raise HTTPException(status_code=400, detail="Job has no sponsor (legacy job)")

    # Close-by-sponsor is restricted to the sponsor. (Human-like role UX)
    if normalize_address(caller) != sponsor:
        raise HTTPException(status_code=403, detail="Only sponsor can close this job")

    subs = s.list_submissions_for_job(job_id)
    if not any(s.get("id") == req.winner_submission_id for s in subs):
        raise HTTPException(status_code=400, detail="winner_submission_id not found for job")

    # close
    job = s.close_job(
        job_id,
        req.winner_submission_id,
        utc_now_iso(),
        close_tx_hash=req.close_tx_hash,
        close_chain_id=req.close_chain_id,
        close_contract_address=req.close_contract_address,
        close_block_number=req.close_block_number,
        close_log_index=req.close_log_index,
    )

    # Notifications: inform participants that the job is closed.
    try:
        _notify_job_closed(store=s, job_id=job_id, winner_submission_id=req.winner_submission_id, actor=caller, via="close")
    except Exception:
        pass

    # Demo rewards (Option A): mint offchain AGR credits to the winning submission author.
    if settings.REWARDS_ENABLED and int(settings.AGR_MINT_PER_WIN) > 0:
        try:
            winner = next((sub for sub in subs if str(sub.get("id") or "") == str(req.winner_submission_id)), None)
            winner_addr = normalize_address(str((winner or {}).get("agent_address") or ""))
            if winner_addr:
                # Idempotency guard (best-effort): avoid duplicate win rewards for the same job/address.
                already = False
                try:
                    rows = s.list_agr_ledger(address=winner_addr, limit=500)
                    already = any(
                        str(r.get("reason") or "").lower() == "win" and str(r.get("job_id") or "") == str(job_id)
                        for r in (rows or [])
                    )
                except Exception:
                    already = False
                if not already:
                    s.agr_credit(
                        address=winner_addr,
                        amount=int(settings.AGR_MINT_PER_WIN),
                        reason="win",
                        job_id=str(job_id),
                    )
        except Exception:
            pass

    # Phase 2 anchoring: create canonical snapshot + root/uri (offchain).
    # Onchain posting is done separately by the operator Safe; receipt is recorded later.
    try:
        anchor = create_job_anchor_snapshot(store=s, job_id=job_id)
        job = dict(job)
        job.update(
            {
                "anchor_root": anchor.get("anchor_root"),
                "anchor_uri": anchor.get("anchor_uri"),
                "anchor_schema_version": anchor.get("schema_version"),
                "anchor_salt": anchor.get("salt"),
                "anchor_tx_hash": anchor.get("anchor_tx_hash"),
                "anchor_chain_id": anchor.get("anchor_chain_id"),
                "anchor_contract_address": anchor.get("anchor_contract_address"),
                "anchor_block_number": anchor.get("anchor_block_number"),
                "anchor_log_index": anchor.get("anchor_log_index"),
            }
        )
    except Exception as e:
        logger.warning("anchor_snapshot_failed: %s", e)

    summary = job_votes(job_id)
    return CloseJobResponse(job=Job(**job), winner_submission_id=req.winner_submission_id, voting_summary=summary)


@app.get("/api/v1/jobs/{job_id}/anchor", response_model=AnchorBatch)
def get_job_anchor(job_id: str, store: Annotated[Store, Depends(store_dep)] = None) -> AnchorBatch:  # type: ignore[assignment]
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    a = store.get_anchor_batch(job_id)
    if not a:
        raise HTTPException(status_code=404, detail="Anchor not found")
    return AnchorBatch(**a)


@app.post("/api/v1/jobs/{job_id}/anchor_receipt", response_model=AnchorBatch)
def record_job_anchor_receipt(
    job_id: str,
    req: RecordAnchorReceiptRequest,
    caller: CurrentAgent,
    store: Annotated[Store, Depends(store_dep)] = None,  # type: ignore[assignment]
) -> AnchorBatch:
    # Operator-only: anchors are posted by operator Safe; record onchain receipt after posting.
    is_operator = normalize_address(caller) in set(settings.OPERATOR_ADDRESSES or [])
    if not is_operator:
        raise HTTPException(status_code=403, detail="Operator access required")
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        a = store.set_anchor_receipt(
            job_id=job_id,
            anchor_tx_hash=req.anchor_tx_hash,
            anchor_chain_id=req.anchor_chain_id,
            anchor_contract_address=req.anchor_contract_address,
            anchor_block_number=req.anchor_block_number,
            anchor_log_index=req.anchor_log_index,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Anchor batch not found (close job first)")
    return AnchorBatch(**a)


@app.post("/api/v1/jobs/{job_id}/finalize", response_model=CloseJobResponse)
def finalize_job(job_id: str, voter: CurrentAgent) -> CloseJobResponse:
    """
    Close a job by final-decision voting tally (Phase 2 governance).
    Requires the caller to be an authenticated participant and to have cast a final vote.
    """
    s = store_dep()
    job = s.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Job already closed")

    # require window end (time-locked finality)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    created_raw = str(job.get("created_at") or "")
    ends_raw = str(job.get("final_vote_ends_at") or "")
    try:
        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else None
        ends = datetime.fromisoformat(ends_raw.replace("Z", "+00:00")) if ends_raw else None
    except Exception:
        created, ends = None, None

    # Back-compat: older jobs may not have a stored window; derive from created_at + default.
    if ends is None and created is not None:
        ends = created + timedelta(seconds=int(settings.FINAL_VOTE_WINDOW_SECONDS))
        ends_raw = ends.isoformat().replace("+00:00", "Z")

    if ends and now < ends:
        raise HTTPException(status_code=400, detail=f"Final voting still open until {ends_raw}")

    # must have at least one final vote from caller
    my_votes = [v for v in s.list_final_votes_for_job(job_id) if v.get("voter_address") == voter.lower()]
    if not my_votes:
        raise HTTPException(status_code=403, detail="Must cast a final vote before finalizing")

    tallies = s.tally_final_votes_for_job(job_id)
    if not tallies:
        raise HTTPException(status_code=400, detail="No final votes for job")
    ordered = list(tallies.values())
    ordered.sort(key=lambda t: int(t.get("votes", 0)), reverse=True)
    winner_submission_id = str(ordered[0]["submission_id"])

    # close using existing close flow (no onchain anchors here)
    job = s.close_job(job_id, winner_submission_id, utc_now_iso())

    # Notifications: inform participants that the job was finalized by voting.
    try:
        _notify_job_closed(store=s, job_id=job_id, winner_submission_id=winner_submission_id, actor=voter, via="finalize")
    except Exception:
        pass

    # Demo rewards (Option A): mint offchain AGR credits to the winning submission author.
    if settings.REWARDS_ENABLED and int(settings.AGR_MINT_PER_WIN) > 0:
        try:
            winner_sub = s.get_submission(winner_submission_id)
            winner_addr = normalize_address(str((winner_sub or {}).get("agent_address") or ""))
            if winner_addr:
                # Idempotency guard (best-effort): avoid duplicate win rewards for the same job/address.
                already = False
                try:
                    rows = s.list_agr_ledger(address=winner_addr, limit=500)
                    already = any(
                        str(r.get("reason") or "").lower() == "win" and str(r.get("job_id") or "") == str(job_id)
                        for r in (rows or [])
                    )
                except Exception:
                    already = False
                if not already:
                    s.agr_credit(
                        address=winner_addr,
                        amount=int(settings.AGR_MINT_PER_WIN),
                        reason="win",
                        job_id=str(job_id),
                    )
        except Exception:
            pass
    summary = job_votes(job_id)
    return CloseJobResponse(job=Job(**job), winner_submission_id=winner_submission_id, voting_summary=summary)


@app.get("/api/v1/reputation/leaderboard", response_model=LeaderboardResponse)
def leaderboard(limit: int = Query(50, ge=1, le=200)) -> LeaderboardResponse:
    s = optional_store_dep()
    if s is None:
        return LeaderboardResponse(entries=[])
    try:
        entries = []
        for r in s.leaderboard(limit=limit):
            entries.append(LeaderboardEntry(address=r["address"], score=float(r["score"]), level=int(r["level"])))
        return LeaderboardResponse(entries=entries)
    except Exception as e:
        logger.warning("leaderboard_unavailable: %s", e)
        return LeaderboardResponse(entries=[])


# ---- Reputation ----
# NOTE: keep this AFTER /reputation/leaderboard, otherwise "leaderboard" may be captured as {address}.
@app.get("/api/v1/reputation/{address}", response_model=Reputation)
def get_reputation(address: str) -> Reputation:
    s = store_dep()
    rep = s.get_rep(address)
    if not rep.get("last_updated_at"):
        rep["last_updated_at"] = utc_now_iso()
    return Reputation(**rep)


# ---- Minimal demo seed ----
@app.on_event("startup")
def seed() -> None:
    # DB is required for most endpoints, but we still want the server to boot in "read-only policy" mode
    # (e.g., /openapi.yaml, /llms.txt, /api/v1/governance/constitution) even if Postgres isn't running yet.
    try:
        s = store_dep()
    except Exception as e:
        logger.warning("startup: DB not ready; skipping demo seed (and any DB-dependent startup): %s", e)
        return

    try:
        # Phase 2: onchain sync should run as a separate process.
        # For local demos, you may opt-in to run it in the API process.
        if settings.ONCHAIN_SYNC_ENABLED and getattr(settings, "ONCHAIN_SYNC_RUN_IN_API", False):
            Thread(target=run_loop, args=(s,), daemon=True).start()

        if s.list_jobs(status="all"):
            return

        now = datetime.now(timezone.utc).replace(microsecond=0)
        ends = now + timedelta(seconds=int(settings.FINAL_VOTE_WINDOW_SECONDS))
        s.create_job(
            {
                "title": "Analyze: Will BTC replace fiat in 10 years?",
                "prompt": "Debate-style brief: argue for/against with evidence. Provide citations with snapshot/hash when possible.",
                "bounty_usdc": 25.0,
                "tags": ["crypto", "macro", "debate"],
                "status": "open",
                "created_at": utc_now_iso(),
                "final_vote_starts_at": now.isoformat().replace("+00:00", "Z"),
                "final_vote_ends_at": ends.isoformat().replace("+00:00", "Z"),
            }
        )
        # For local demo only: give a tiny stake to a known address if desired by env later.
    except Exception as e:
        logger.warning("startup: DB not ready; skipping demo seed/onchain loop: %s", e)
        return

