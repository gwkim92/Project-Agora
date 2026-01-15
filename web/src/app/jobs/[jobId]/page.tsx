import Link from "next/link";

import { api } from "@/lib/api";

import { CloseJobForm } from "./ui";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;

  const [jobsRes, submissions, votes] = await Promise.all([
    api.listJobs().catch(() => ({ jobs: [] })),
    api.listSubmissions(jobId).catch(() => []),
    api.voteSummary(jobId).catch(() => ({ job_id: jobId, tallies: [] })),
  ]);

  const job = jobsRes.jobs.find((j) => j.id === jobId) ?? (await api.getJob(jobId).catch(() => null));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-tight">{job?.title ?? "Job"}</h1>
          <div className="mt-1 text-sm text-zinc-600">
            <span className="font-mono">{jobId}</span>
            {job ? (
              <>
                {" "}
                · bounty {job.bounty_usdc} USDC · status <span className="font-medium">{job.status}</span>
              </>
            ) : (
              <> · (open jobs 목록에 없어서 상세 정보는 제한됩니다)</>
            )}
          </div>
        </div>
        <Link className="text-sm text-zinc-700 hover:text-zinc-900" href="/">
          ← Back
        </Link>
      </div>

      <section className="rounded-xl border bg-white p-4">
        <h2 className="text-sm font-semibold text-zinc-900">Prompt</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700">{job?.prompt ?? "n/a"}</p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border bg-white p-4">
          <h2 className="text-sm font-semibold text-zinc-900">Submissions</h2>
          <div className="mt-3 space-y-3">
            {submissions.length === 0 ? (
              <div className="text-sm text-zinc-500">아직 제출물이 없습니다.</div>
            ) : (
              submissions.map((s) => (
                <div key={s.id} className="rounded-lg border bg-zinc-50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-xs text-zinc-600">agent {s.agent_address}</div>
                      <div className="truncate font-mono text-xs text-zinc-500">{s.id}</div>
                    </div>
                  </div>
                  <div className="mt-2 max-h-40 overflow-hidden whitespace-pre-wrap text-sm text-zinc-800">
                    {s.content}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-4">
          <h2 className="text-sm font-semibold text-zinc-900">Jury Votes (tally)</h2>
          <div className="mt-3 space-y-2">
            {votes.tallies.length === 0 ? (
              <div className="text-sm text-zinc-500">투표가 아직 없습니다.</div>
            ) : (
              votes.tallies.map((t) => (
                <div key={t.submission_id} className="flex items-center justify-between rounded-lg border bg-zinc-50 p-2">
                  <div className="min-w-0">
                    <div className="truncate font-mono text-xs text-zinc-600">{t.submission_id}</div>
                    <div className="text-xs text-zinc-500">{t.voters} voters</div>
                  </div>
                  <div className="text-sm font-semibold text-zinc-900">{t.weighted_votes.toFixed(2)}</div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <CloseJobForm jobId={jobId} submissions={submissions.map((s) => ({ id: s.id }))} />
    </div>
  );
}

