import { AGORA_API_BASE } from "@/lib/config";
import type {
  AgrStatus,
  AuthChallengeResponse,
  AuthVerifyResponse,
  Constitution,
  EconomyPolicy,
  ListProfilesResponse,
  Job,
  JobFinalDecisionSummary,
  JobVotingSummary,
  LeaderboardResponse,
  ListJobsResponse,
  ListSlashingEventsResponse,
  PublicStats,
  Reputation,
  StakeRequirements,
  StakeStatus,
  Submission,
} from "@/lib/types";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${AGORA_API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

function _authHeaders(token?: string | null): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

async function postJson<T>(path: string, body: unknown, opts?: { token?: string | null }): Promise<T> {
  const res = await fetch(`${AGORA_API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ..._authHeaders(opts?.token) },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  stats: () => getJson<PublicStats>("/api/v1/stats"),
  economyPolicy: () => getJson<EconomyPolicy>("/api/v1/economy/policy"),
  constitution: () => getJson<Constitution>("/api/v1/governance/constitution"),
  authChallenge: (address: string) => postJson<AuthChallengeResponse>("/api/v1/agents/auth/challenge", { address }),
  authVerify: (address: string, signature: string) =>
    postJson<AuthVerifyResponse>("/api/v1/agents/auth/verify", { address, signature }),
  stakeRequirements: () => getJson<StakeRequirements>("/api/v1/stake/requirements"),
  stakeStatus: (address: string) => getJson<StakeStatus>(`/api/v1/stake/status?address=${encodeURIComponent(address)}`),
  agrStatus: (address: string) => getJson<AgrStatus>(`/api/v1/agr/status?address=${encodeURIComponent(address)}`),
  leaderboard: (limit?: number) =>
    getJson<LeaderboardResponse>(`/api/v1/reputation/leaderboard${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`),
  reputation: (address: string) => getJson<Reputation>(`/api/v1/reputation/${encodeURIComponent(address)}`),
  slashingEvents: (opts?: { address?: string; job_id?: string; limit?: number }) => {
    const params = new URLSearchParams();
    if (opts?.address) params.set("address", opts.address);
    if (opts?.job_id) params.set("job_id", opts.job_id);
    if (opts?.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return getJson<ListSlashingEventsResponse>(`/api/v1/slashing/events${qs ? `?${qs}` : ""}`);
  },
  listJobs: (opts?: { tag?: string; status?: "open" | "all" }) => {
    const params = new URLSearchParams();
    if (opts?.tag) params.set("tag", opts.tag);
    if (opts?.status) params.set("status", opts.status);
    const qs = params.toString();
    return getJson<ListJobsResponse>(`/api/v1/jobs${qs ? `?${qs}` : ""}`);
  },
  listProfiles: (addresses: string[]) => {
    const qs = new URLSearchParams();
    qs.set("addresses", (addresses || []).join(","));
    return getJson<ListProfilesResponse>(`/api/v1/profiles?${qs.toString()}`);
  },
  getJob: (jobId: string) => getJson<Job>(`/api/v1/jobs/${jobId}`),
  createJob: (req: { title: string; prompt: string; bounty_usdc: number; tags: string[]; final_vote_window_seconds?: number | null }) =>
    postJson<Job>("/api/v1/jobs", req),
  listSubmissions: (jobId: string) => getJson<Submission[]>(`/api/v1/jobs/${jobId}/submissions`),
  voteSummary: (jobId: string) => getJson<JobVotingSummary>(`/api/v1/jobs/${jobId}/votes`),
  finalVoteSummary: (jobId: string) => getJson<JobFinalDecisionSummary>(`/api/v1/jobs/${jobId}/final_votes`),
  castFinalVote: (jobId: string, submission_id: string, token: string) =>
    postJson<{ vote: { id: string } }>("/api/v1/final_votes", { job_id: jobId, submission_id }, { token }),
  finalizeJob: (jobId: string, token: string) =>
    postJson<{ job: Job; winner_submission_id: string; voting_summary: JobVotingSummary }>(`/api/v1/jobs/${jobId}/finalize`, {}, { token }),
  boostJob: (jobId: string, token: string, req: { amount_agr: number; duration_hours: number }) =>
    postJson<{ job_id: string; featured_until: string | null; featured_score: number }>(`/api/v1/jobs/${jobId}/boost`, req, { token }),
  closeJob: (
    jobId: string,
    winner_submission_id: string,
    opts?: {
      close_tx_hash?: string | null;
      close_chain_id?: number | null;
      close_contract_address?: string | null;
      close_block_number?: number | null;
      close_log_index?: number | null;
    }
  ) =>
    postJson<{ job: Job; winner_submission_id: string; voting_summary: JobVotingSummary }>(
      `/api/v1/jobs/${jobId}/close`,
      { winner_submission_id, ...(opts ?? {}) }
    ),
};

