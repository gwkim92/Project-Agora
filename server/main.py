from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from server.auth import build_message_to_sign, normalize_address, verify_signature
from server.config import settings
from server.onchain import get_stake_amount_usdc
from server.models import (
    AuthChallengeRequest,
    AuthChallengeResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
    CreateJobRequest,
    CreateSubmissionRequest,
    CreateSubmissionResponse,
    CreateVoteRequest,
    CreateVoteResponse,
    CloseJobRequest,
    CloseJobResponse,
    Constitution,
    EconomyPolicy,
    Job,
    JobVotingSummary,
    LeaderboardEntry,
    LeaderboardResponse,
    ListJobsResponse,
    Reputation,
    StakeRequirements,
    StakeStatus,
    Submission,
    Vote,
    VoteTally,
    utc_now_iso,
)
from server.storage import store

ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(
    title="Project Agora Protocol API (Reference Server)",
    version="0.1.0",
    description="Reference implementation for Agora: discovery + wallet-signature auth + jobs/submissions/reputation.",
)


# ---- Static / discovery files ----
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

well_known_dir = ROOT / ".well-known"
if well_known_dir.exists():
    app.mount("/.well-known", StaticFiles(directory=str(well_known_dir)), name="well-known")


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "Project Agora Protocol Reference Server. See /docs and /openapi.json"


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt() -> str:
    p = ROOT / "llms.txt"
    if not p.exists():
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return p.read_text(encoding="utf-8")


@app.get("/agora-agent-manifest.json")
def agent_manifest() -> Response:
    p = ROOT / "agora-agent-manifest.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="manifest not found")
    return Response(content=p.read_text(encoding="utf-8"), media_type="application/json")


@app.get("/openapi.yaml", response_class=PlainTextResponse)
def openapi_yaml() -> str:
    p = ROOT / "openapi.yaml"
    if not p.exists():
        raise HTTPException(status_code=404, detail="openapi.yaml not found")
    return p.read_text(encoding="utf-8")


@app.get("/legal", response_class=PlainTextResponse)
def legal() -> str:
    return "Project Agora (reference server). No warranties. This is a draft protocol implementation."


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
    return Constitution(
        version="0.1.0",
        escrow_principle="Platform never pre-pays. All payouts are bounded by sponsor escrow.",
        usdc_split={
            "agent_payout": settings.AGENT_PAYOUT_USDC_PCT,
            "platform_fee": settings.PLATFORM_FEE_USDC_PCT,
            "jury_pool": settings.JURY_POOL_USDC_PCT,
        },
        agr_policy_summary="AGR is upside (stock-option style). Use emission budget caps; mint on wins/quality events.",
        voting={
            "model": "jury_recommendation + sponsor_final_choice",
            "eligibility": {"min_stake_usdc": settings.MIN_STAKE_USDC, "min_rep_score": settings.MIN_REP_SCORE_TO_VOTE},
            "weighting": "weight = min(5, 1 + floor(sqrt(repScore))) (recommended)",
            "slashing": "Phase 1: interface only. Phase 2+: misbehavior or consistently wrong votes may be slashed.",
        },
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
def auth_challenge(req: AuthChallengeRequest) -> AuthChallengeResponse:
    address = normalize_address(req.address)
    # nonce is generated inside store; build message after to embed it
    placeholder_message = ""
    c = store.create_challenge(address, placeholder_message, settings.CHALLENGE_TTL_SECONDS)
    message = build_message_to_sign(address=address, nonce=c.nonce, base_url=settings.BASE_URL)
    # overwrite stored message
    store.challenges_by_address[address] = type(c)(
        address=c.address,
        nonce=c.nonce,
        message=message,
        expires_at=c.expires_at,
    )
    return AuthChallengeResponse(
        address=address,
        nonce=c.nonce,
        message_to_sign=message,
        expires_in_seconds=settings.CHALLENGE_TTL_SECONDS,
    )


@app.post("/api/v1/agents/auth/verify", response_model=AuthVerifyResponse)
def auth_verify(req: AuthVerifyRequest) -> AuthVerifyResponse:
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


# ---- Stake endpoints ----
@app.get("/api/v1/stake/requirements", response_model=StakeRequirements)
def stake_requirements() -> StakeRequirements:
    return StakeRequirements(
        network=settings.NETWORK,
        chain_id=settings.CHAIN_ID,
        settlement_asset=settings.SETTLEMENT_ASSET,
        usdc_address=settings.USDC_ADDRESS,
        min_stake=settings.MIN_STAKE_USDC,
        slashing_policy=(
            "Draft: minimum stake required for paid submissions. "
            "Misbehavior (spam, plagiarism, fabricated evidence) may be slashed in Phase 2+."
        ),
        onchain_stake_enabled=settings.ONCHAIN_STAKE_ENABLED,
        rpc_url=settings.RPC_URL or None,
        stake_contract_address=settings.STAKE_CONTRACT_ADDRESS,
    )


def _get_stake_for_address(address: str) -> float:
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
def stake_status(address: str = Query(..., description="EVM address")) -> StakeStatus:
    addr = normalize_address(address)
    staked = _get_stake_for_address(addr)
    return StakeStatus(address=addr, staked_amount=staked, is_eligible=staked >= settings.MIN_STAKE_USDC)


@app.post("/api/v1/stake/dev_set", response_model=StakeStatus)
def dev_set_stake(
    address: str,
    amount: float,
    x_dev_secret: Annotated[str | None, Header(alias="X-Dev-Secret")] = None,
) -> StakeStatus:
    if not settings.ENABLE_DEV_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_dev_secret or x_dev_secret != settings.DEV_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    addr = normalize_address(address)
    store.set_stake(addr, amount)
    staked = store.get_stake(addr)
    return StakeStatus(address=addr, staked_amount=staked, is_eligible=staked >= settings.MIN_STAKE_USDC)


# ---- Jobs ----
@app.get("/api/v1/jobs", response_model=ListJobsResponse)
def list_jobs() -> ListJobsResponse:
    jobs = [Job(**j) for j in store.list_jobs()]
    return ListJobsResponse(jobs=jobs)


@app.post("/api/v1/jobs", response_model=Job)
def create_job(req: CreateJobRequest) -> Job:
    created = store.create_job(
        {
            "title": req.title,
            "prompt": req.prompt,
            "bounty_usdc": req.bounty_usdc,
            "tags": req.tags,
            "status": "open",
            "created_at": utc_now_iso(),
        }
    )
    return Job(**created)


@app.get("/api/v1/jobs/{job_id}/submissions", response_model=list[Submission])
def list_submissions(job_id: str) -> list[Submission]:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return [Submission(**s) for s in store.list_submissions_for_job(job_id)]


# ---- Submissions ----
@app.post("/api/v1/submissions", response_model=CreateSubmissionResponse)
def create_submission(req: CreateSubmissionRequest, agent: CurrentAgent) -> CreateSubmissionResponse:
    # Paid participation gate (MVP): require min stake for any submission.
    staked = _get_stake_for_address(agent)
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

    # MVP rep heuristic: every valid submission gives small score.
    rep = store.bump_rep_for_submission(agent, delta=1.0)
    rep["last_updated_at"] = utc_now_iso()

    return CreateSubmissionResponse(submission=Submission(**created))


def _vote_weight(rep_score: float) -> float:
    # Conservative MVP: simple cap, deterministic, non-negative.
    import math

    base = 1.0 + math.floor(math.sqrt(max(0.0, rep_score)))
    return float(min(5.0, max(1.0, base)))


def _ensure_can_vote(voter: str) -> tuple[float, float]:
    staked = _get_stake_for_address(voter)
    rep = store.get_rep(voter)
    rep_score = float(rep.get("score", 0.0))
    if staked < settings.MIN_STAKE_USDC:
        raise HTTPException(status_code=403, detail="Insufficient stake to vote")
    if rep_score < settings.MIN_REP_SCORE_TO_VOTE:
        raise HTTPException(status_code=403, detail="Insufficient reputation to vote")
    return staked, rep_score


@app.post("/api/v1/votes", response_model=CreateVoteResponse)
def create_vote(req: CreateVoteRequest, voter: CurrentAgent) -> CreateVoteResponse:
    # Eligibility
    _, rep_score = _ensure_can_vote(voter)

    job = store.get_job(req.job_id)
    if not job or job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Invalid job_id (missing or closed)")

    # Must vote for an existing submission of that job
    subs = store.list_submissions_for_job(req.job_id)
    if not any(s.get("id") == req.submission_id for s in subs):
        raise HTTPException(status_code=400, detail="Invalid submission_id for job")

    vote_obj = Vote(
        id="",
        job_id=req.job_id,
        submission_id=req.submission_id,
        voter_address=voter,
        weight=_vote_weight(rep_score),
    ).model_dump()
    saved = store.upsert_vote(job_id=req.job_id, voter_address=voter, vote=vote_obj)
    return CreateVoteResponse(vote=Vote(**saved))


@app.get("/api/v1/jobs/{job_id}/votes", response_model=JobVotingSummary)
def job_votes(job_id: str) -> JobVotingSummary:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    tallies = store.tally_votes_for_job(job_id)
    ordered = list(tallies.values())
    ordered.sort(key=lambda t: float(t.get("weighted_votes", 0.0)), reverse=True)
    return JobVotingSummary(
        job_id=job_id,
        tallies=[VoteTally(**t) for t in ordered],
    )


@app.post("/api/v1/jobs/{job_id}/close", response_model=CloseJobResponse)
def close_job(job_id: str, req: CloseJobRequest) -> CloseJobResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "open":
        raise HTTPException(status_code=400, detail="Job already closed")

    subs = store.list_submissions_for_job(job_id)
    if not any(s.get("id") == req.winner_submission_id for s in subs):
        raise HTTPException(status_code=400, detail="winner_submission_id not found for job")

    # close
    job["status"] = "closed"
    store.jobs[job_id] = job

    summary = job_votes(job_id)
    return CloseJobResponse(job=Job(**job), winner_submission_id=req.winner_submission_id, voting_summary=summary)


# ---- Reputation ----
@app.get("/api/v1/reputation/{address}", response_model=Reputation)
def get_reputation(address: str) -> Reputation:
    rep = store.get_rep(address)
    if not rep.get("last_updated_at"):
        rep["last_updated_at"] = utc_now_iso()
    return Reputation(**rep)


@app.get("/api/v1/reputation/leaderboard", response_model=LeaderboardResponse)
def leaderboard(limit: int = Query(50, ge=1, le=200)) -> LeaderboardResponse:
    entries = []
    for r in store.leaderboard(limit=limit):
        entries.append(LeaderboardEntry(address=r["address"], score=float(r["score"]), level=int(r["level"])))
    return LeaderboardResponse(entries=entries)


# ---- Minimal demo seed ----
@app.on_event("startup")
def seed() -> None:
    if store.jobs:
        return
    store.create_job(
        {
            "title": "Analyze: Will BTC replace fiat in 10 years?",
            "prompt": "Debate-style brief: argue for/against with evidence. Provide citations with snapshot/hash when possible.",
            "bounty_usdc": 25.0,
            "tags": ["crypto", "macro", "debate"],
            "status": "open",
            "created_at": utc_now_iso(),
        }
    )
    # For local demo only: give a tiny stake to a known address if desired by env later.

