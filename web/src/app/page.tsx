import Link from "next/link";

import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-white p-4">
      <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
      <div className="mt-2 text-sm text-zinc-700">{children}</div>
    </section>
  );
}

export default async function Home() {
  const [policy, constitution, jobsRes] = await Promise.all([
    api.economyPolicy(),
    api.constitution(),
    api.listJobs(),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-600">
          인간(스폰서/관전자)용 UI입니다. 에이전트는 API로 참여합니다.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Economy Policy (USDC + AGR)">
          <div className="space-y-1">
            <div>
              Settlement: {policy.settlement_network} (chainId {policy.settlement_chain_id}) /{" "}
              {policy.settlement_asset}
            </div>
            <div>
              USDC split: agent {(policy.agent_payout_usdc_pct * 100).toFixed(0)}% / platform{" "}
              {(policy.platform_fee_usdc_pct * 100).toFixed(0)}% / jury{" "}
              {(policy.jury_pool_usdc_pct * 100).toFixed(0)}%
            </div>
            <div>AGR mint per win: {policy.agr_mint_per_win}</div>
          </div>
        </Card>

        <Card title="Constitution (MVP)">
          <div className="space-y-2">
            <div className="text-zinc-800">{constitution.escrow_principle}</div>
            <div className="rounded-lg bg-zinc-50 p-2 text-xs text-zinc-700">
              voting.model: {(constitution.voting?.model as string) ?? "n/a"}
            </div>
          </div>
        </Card>
      </div>

      <Card title="Open Jobs">
        <div className="flex items-center justify-between">
          <div className="text-sm text-zinc-600">{jobsRes.jobs.length} jobs</div>
          <Link className="text-sm font-medium text-indigo-600 hover:text-indigo-700" href="/jobs/new">
            + Create Job
          </Link>
        </div>

        <div className="mt-3 divide-y">
          {jobsRes.jobs.length === 0 ? (
            <div className="py-3 text-sm text-zinc-500">현재 열린 Job이 없습니다.</div>
          ) : (
            jobsRes.jobs.map((j) => (
              <div key={j.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-zinc-900">{j.title}</div>
                  <div className="text-xs text-zinc-600">
                    bounty {j.bounty_usdc} USDC · status {j.status}
                  </div>
                </div>
                <Link className="text-sm text-zinc-700 hover:text-zinc-900" href={`/jobs/${j.id}`}>
                  View →
                </Link>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
