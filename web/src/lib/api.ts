import { AGORA_API_BASE } from "@/lib/config";
import type { Constitution, EconomyPolicy, Job, JobVotingSummary, ListJobsResponse, Submission } from "@/lib/types";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${AGORA_API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${AGORA_API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  economyPolicy: () => getJson<EconomyPolicy>("/api/v1/economy/policy"),
  constitution: () => getJson<Constitution>("/api/v1/governance/constitution"),
  listJobs: () => getJson<ListJobsResponse>("/api/v1/jobs"),
  getJob: (jobId: string) => getJson<Job>(`/api/v1/jobs/${jobId}`),
  createJob: (req: { title: string; prompt: string; bounty_usdc: number; tags: string[] }) =>
    postJson<Job>("/api/v1/jobs", req),
  listSubmissions: (jobId: string) => getJson<Submission[]>(`/api/v1/jobs/${jobId}/submissions`),
  voteSummary: (jobId: string) => getJson<JobVotingSummary>(`/api/v1/jobs/${jobId}/votes`),
  closeJob: (jobId: string, winner_submission_id: string) =>
    postJson<{ job: Job; winner_submission_id: string; voting_summary: JobVotingSummary }>(
      `/api/v1/jobs/${jobId}/close`,
      { winner_submission_id }
    ),
};

