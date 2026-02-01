import { cache } from "react";
import { api } from "@/lib/api";

/**
 * Server Component helper: de-duplicate identical offchain API calls within a single request.
 *
 * Note:
 * - This does NOT enable Next.js fetch caching (we use cache: "no-store" in api.ts).
 * - It only prevents accidental duplicate calls in the same render pass/request.
 */
export const serverApi = {
  constitution: cache(() => api.constitution()),
  economyPolicy: cache(() => api.economyPolicy()),
  stakeRequirements: cache(() => api.stakeRequirements()),
  leaderboard: cache((limit?: number) => api.leaderboard(limit)),
  listJobs: cache((opts?: { tag?: string; status?: "open" | "all" }) => api.listJobs(opts)),
  getJob: cache((jobId: string) => api.getJob(jobId)),
  listSubmissions: cache((jobId: string) => api.listSubmissions(jobId)),
  voteSummary: cache((jobId: string) => api.voteSummary(jobId)),
  finalVoteSummary: cache((jobId: string) => api.finalVoteSummary(jobId)),
};

