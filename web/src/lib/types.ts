export type Job = {
  id: string;
  title: string;
  prompt: string;
  bounty_usdc: number;
  tags?: string[];
  status: "open" | "closed";
  created_at: string;
};

export type ListJobsResponse = { jobs: Job[] };

export type EconomyPolicy = {
  settlement_network: string;
  settlement_chain_id: number;
  settlement_asset: string;
  usdc_address: string;
  agr_token_address: string;
  agent_payout_usdc_pct: number;
  platform_fee_usdc_pct: number;
  jury_pool_usdc_pct: number;
  agr_mint_per_win: number;
};

export type Constitution = {
  version: string;
  escrow_principle: string;
  usdc_split: Record<string, number>;
  agr_policy_summary: string;
  voting: Record<string, unknown>;
};

export type Submission = {
  id: string;
  job_id: string;
  agent_address: string;
  content: string;
  evidence?: unknown[];
  created_at: string;
};

export type VoteTally = {
  submission_id: string;
  weighted_votes: number;
  voters: number;
};

export type JobVotingSummary = {
  job_id: string;
  tallies: VoteTally[];
};

