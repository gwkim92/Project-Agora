export type Job = {
  id: string;
  title: string;
  prompt: string;
  bounty_usdc: number;
  tags?: string[];
  status: "open" | "closed";
  sponsor_address?: string | null;
  created_at: string;
  winner_submission_id?: string | null;
  closed_at?: string | null;
  close_tx_hash?: string | null;
  close_chain_id?: number | null;
  close_contract_address?: string | null;
  close_block_number?: number | null;
  close_log_index?: number | null;
  final_vote_starts_at?: string | null;
  final_vote_ends_at?: string | null;
  featured_until?: string | null;
  featured_score?: number | null;
  anchor_root?: string | null;
  anchor_uri?: string | null;
  anchor_schema_version?: number | null;
  anchor_salt?: string | null;
  anchor_tx_hash?: string | null;
  anchor_chain_id?: number | null;
  anchor_contract_address?: string | null;
  anchor_block_number?: number | null;
  anchor_log_index?: number | null;
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

export type TreasuryInfo = {
  network: string;
  chain_id: number;
  contract_address: string;
  usdc_address: string;
  note?: string | null;
};

export type Constitution = {
  version: string;
  escrow_principle: string;
  usdc_split: Record<string, number>;
  agr_policy_summary: string;
  voting: Record<string, unknown>;
  treasury?: TreasuryInfo | null;
};

export type Evidence = {
  type?: string | null;
  source_url?: string | null;
  retrieved_at?: string | null;
  snapshot_uri?: string | null;
  snapshot_hash?: string | null;
  quote?: string | null;
  claim?: string | null;
  confidence?: number | null;
  metadata?: Record<string, unknown> | null;
};

export type Submission = {
  id: string;
  job_id: string;
  agent_address: string;
  content: string;
  evidence?: Evidence[];
  created_at: string;
};

export type Comment = {
  id: string;
  target_type: "job" | "submission";
  target_id: string;
  parent_id?: string | null;
  author_address: string;
  content: string;
  created_at: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
};

export type ListCommentsResponse = {
  comments: Comment[];
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

export type AuthChallengeResponse = {
  address: string;
  nonce: string;
  message_to_sign: string;
  expires_in_seconds: number;
};

export type AuthVerifyResponse = {
  access_token: string;
  token_type: "bearer";
};

export type StakeStatus = {
  address: string;
  is_eligible: boolean;
  staked_amount: number;
  stake_tx_hash?: string | null;
  stake_chain_id?: number | null;
  stake_contract_address?: string | null;
  stake_block_number?: number | null;
  stake_log_index?: number | null;
};

export type StakeRequirements = {
  network: string;
  chain_id: number;
  settlement_asset: string;
  usdc_address: string;
  min_stake: number;
  slashing_policy: string;
  onchain_stake_enabled?: boolean | null;
  rpc_url?: string | null;
  stake_contract_address?: string | null;
};

export type AgrStatus = {
  address: string;
  balance: number;
  earned: number;
  spent: number;
};

export type Reputation = {
  address: string;
  score: number;
  level: number;
  wins: number;
  losses: number;
  badges?: string[];
  last_updated_at: string;
};

export type AgentProfile = {
  address: string;
  nickname: string | null;
  avatar_url: string | null;
  avatar_mode: "manual" | "donor";
  participant_type?: "unknown" | "human" | "agent";
  avatar_seed?: string | null;
  updated_at: string;
};

export type ListProfilesResponse = {
  profiles: AgentProfile[];
};

export type AdminMetrics = {
  users: number;
  jobs_total: number;
  jobs_open: number;
  submissions_total: number;
  comments_total: number;
  votes_total: number;
  final_votes_total: number;
  active_sessions: number;
};

export type LeaderboardEntry = {
  address: string;
  score: number;
  level: number;
};

export type LeaderboardResponse = {
  entries: LeaderboardEntry[];
};

export type PublicStats = {
  users_total: number;
};

export type SlashingEvent = {
  id: string;
  agent_address: string;
  amount_usdc: number;
  recipient_address?: string | null;
  job_id?: string | null;
  tx_hash?: string | null;
  chain_id?: number | null;
  contract_address?: string | null;
  block_number?: number | null;
  log_index?: number | null;
  created_at: string;
};

export type ListSlashingEventsResponse = {
  events: SlashingEvent[];
};

export type FinalVoteTally = {
  submission_id: string;
  votes: number;
  voters: number;
};

export type JobFinalDecisionSummary = {
  job_id: string;
  tallies: FinalVoteTally[];
};
