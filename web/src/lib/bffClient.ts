async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
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

async function putJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`PUT ${path} failed: ${res.status} ${text}`);
  }
  return (await res.json()) as T;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET ${path} failed: ${res.status} ${text}`);
  }
  return (await res.json()) as T;
}

export const bff = {
  authMe: () => getJson<{ authenticated: boolean; address: string | null }>("/api/auth/me"),
  authChallenge: (address: string) =>
    postJson<{ address: string; nonce: string; message_to_sign: string; expires_in_seconds: number }>("/api/auth/challenge", { address }),
  authVerify: (address: string, signature: string) =>
    postJson<{ ok: boolean; address: string }>("/api/auth/verify", { address, signature }),
  authLogout: () => postJson<{ ok: boolean }>("/api/auth/logout", {}),

  getProfile: () =>
    getJson<{
      address: string;
      nickname: string | null;
      avatar_url: string | null;
      avatar_mode: "manual" | "donor";
      participant_type?: "unknown" | "human" | "agent";
      avatar_seed?: string | null;
      updated_at: string;
    }>("/api/profile"),
  updateProfile: (req: {
    nickname?: string | null;
    avatar_url?: string | null;
    avatar_mode?: "manual" | "donor";
    participant_type?: "unknown" | "human" | "agent";
  }) =>
    putJson<{
      address: string;
      nickname: string | null;
      avatar_url: string | null;
      avatar_mode: "manual" | "donor";
      participant_type?: "unknown" | "human" | "agent";
      avatar_seed?: string | null;
      updated_at: string;
    }>("/api/profile", req),

  listProfiles: (addresses: string[]) => {
    const qs = new URLSearchParams();
    qs.set("addresses", (addresses || []).join(","));
    return getJson<{ profiles: Array<Record<string, unknown>> }>(`/api/profiles?${qs.toString()}`);
  },

  notifications: (opts?: { unread_only?: boolean; limit?: number }) => {
    const qs = new URLSearchParams();
    if (opts?.unread_only) qs.set("unread_only", "true");
    if (opts?.limit) qs.set("limit", String(opts.limit));
    const q = qs.toString();
    return getJson<{ notifications: Array<Record<string, unknown>>; count: number }>(`/api/notifications${q ? `?${q}` : ""}`);
  },
  markNotificationRead: (id: string) => postJson<{ id: string; read_at: string }>(`/api/notifications/${encodeURIComponent(id)}/read`, {}),

  adminMetrics: () =>
    getJson<{
      users: number;
      jobs_total: number;
      jobs_open: number;
      submissions_total: number;
      comments_total: number;
      votes_total: number;
      final_votes_total: number;
      active_sessions: number;
    }>("/api/admin/metrics"),

  adminOnchainCursors: (limit?: number) =>
    getJson<{ cursors: Array<{ key: string; last_block: number; updated_at: string }> }>(
      `/api/admin/onchain/cursors${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`
    ),
  adminSetOnchainCursor: (body: { key: string; last_block: number }) =>
    postJson<{ key: string; last_block: number; updated_at: string }>("/api/admin/onchain/cursors", body),
  adminSuggestedCursorKeys: () => getJson<{ keys: string[] }>("/api/admin/onchain/suggested_cursor_keys"),
  adminSyncOnce: () => postJson<Record<string, unknown>>("/api/admin/onchain/sync_once", {}),

  adminDonationEvents: (limit?: number) =>
    getJson<{
      events: Array<{
        id: string;
        donor_address: string;
        asset_address: string;
        amount_raw: number;
        amount_usd: number | null;
        purpose_id: number | null;
        memo_hash: string | null;
        tx_hash: string;
        chain_id: number;
        contract_address: string;
        block_number: number;
        log_index: number;
        created_at: string;
      }>;
    }>(`/api/admin/donations/events${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`),

  adminAnchors: (limit?: number) =>
    getJson<{
      anchors: Array<{
        id: string;
        job_id: string;
        schema_version: number;
        salt: string;
        anchor_root: string;
        anchor_uri: string;
        anchor_tx_hash: string | null;
        anchor_chain_id: number | null;
        anchor_contract_address: string | null;
        anchor_block_number: number | null;
        anchor_log_index: number | null;
        created_at: string;
      }>;
    }>(`/api/admin/anchors${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`),

  adminRecordAnchorReceipt: (body: {
    job_id: string;
    anchor_tx_hash: string;
    anchor_chain_id: number;
    anchor_contract_address: string;
    anchor_block_number: number;
    anchor_log_index: number;
  }) => postJson<Record<string, unknown>>("/api/admin/jobs/anchor_receipt", body),

  adminPrepareAnchorTx: (jobId: string) =>
    postJson<{
      chain_id: number;
      to: string;
      data: string;
      value_wei: number;
      anchor: {
        id: string;
        job_id: string;
        schema_version: number;
        salt: string;
        anchor_root: string;
        anchor_uri: string;
        anchor_tx_hash: string | null;
        anchor_chain_id: number | null;
        anchor_contract_address: string | null;
        anchor_block_number: number | null;
        anchor_log_index: number | null;
        created_at: string;
      };
    }>(`/api/admin/anchors/${encodeURIComponent(jobId)}/prepare`, {}),

  adminBroadcastAnchorTx: (jobId: string) =>
    postJson<{
      id: string;
      job_id: string;
      schema_version: number;
      salt: string;
      anchor_root: string;
      anchor_uri: string;
      anchor_tx_hash: string | null;
      anchor_chain_id: number | null;
      anchor_contract_address: string | null;
      anchor_block_number: number | null;
      anchor_log_index: number | null;
      created_at: string;
    }>(`/api/admin/anchors/${encodeURIComponent(jobId)}/broadcast`, {}),

  listPosts: (opts?: { tag?: string | null; limit?: number | null }) => {
    const qs = new URLSearchParams();
    if (opts?.tag) qs.set("tag", String(opts.tag));
    if (opts?.limit != null) qs.set("limit", String(opts.limit));
    const q = qs.toString() ? `?${qs.toString()}` : "";
    return getJson<{ posts: Array<Record<string, unknown>> }>(`/api/posts${q}`);
  },
  createPost: (req: { title: string; content: string; tags: string[] }) => postJson<{ id: string }>("/api/posts", req),
  getPost: (postId: string) => getJson<Record<string, unknown>>(`/api/posts/${postId}`),

  createJob: (req: { title: string; prompt: string; bounty_usdc: number; tags: string[]; final_vote_window_seconds?: number | null }) =>
    postJson<{ id: string }>("/api/jobs", req),
  closeJob: (
    jobId: string,
    body: {
      winner_submission_id: string;
      close_tx_hash?: string | null;
      close_chain_id?: number | null;
      close_contract_address?: string | null;
      close_block_number?: number | null;
      close_log_index?: number | null;
    }
  ) => postJson<{ job: unknown; winner_submission_id: string }>(`/api/jobs/${jobId}/close`, body),

  castJuryVote: (jobId: string, submission_id: string, review?: Record<string, unknown> | null) =>
    postJson<{ vote: unknown }>("/api/votes", { job_id: jobId, submission_id, review: review ?? null }),

  submitWork: (req: { job_id: string; content: string; evidence: unknown[] }) =>
    postJson<{ submission: { id: string } }>("/api/submissions", req),

  listJobComments: (jobId: string, limit?: number) =>
    getJson<{ comments: Array<Record<string, unknown>> }>(`/api/jobs/${jobId}/comments${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`),
  postJobComment: (jobId: string, body: { content: string; parent_id?: string | null }) =>
    postJson<{ comment: unknown }>(`/api/jobs/${jobId}/comments`, body),

  listSubmissionComments: (submissionId: string, limit?: number) =>
    getJson<{ comments: Array<Record<string, unknown>> }>(
      `/api/submissions/${submissionId}/comments${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`
    ),
  postSubmissionComment: (submissionId: string, body: { content: string; parent_id?: string | null }) =>
    postJson<{ comment: unknown }>(`/api/submissions/${submissionId}/comments`, body),

  listPostComments: (postId: string, limit?: number) =>
    getJson<{ comments: Array<Record<string, unknown>> }>(`/api/posts/${postId}/comments${limit ? `?limit=${encodeURIComponent(String(limit))}` : ""}`),
  postPostComment: (postId: string, body: { content: string; parent_id?: string | null }) =>
    postJson<{ comment: unknown }>(`/api/posts/${postId}/comments`, body),
  deleteComment: (commentId: string) =>
    fetch(`/api/comments/${commentId}`, { method: "DELETE" }).then(async (r) => {
      const t = await r.text().catch(() => "");
      if (!r.ok) throw new Error(t || `DELETE /api/comments/${commentId} failed`);
      return JSON.parse(t) as unknown;
    }),

  castFinalVote: (jobId: string, submission_id: string) =>
    postJson<{ vote: { id: string } }>("/api/final_votes", { job_id: jobId, submission_id }),
  finalizeJob: (jobId: string) =>
    postJson<{ job: unknown; winner_submission_id: string }> (`/api/jobs/${jobId}/finalize`, {}),
  boostJob: (jobId: string, req: { amount_agr: number; duration_hours: number }) =>
    postJson<{ job_id: string; featured_until: string | null; featured_score: number }>(`/api/jobs/${jobId}/boost`, req),
};

