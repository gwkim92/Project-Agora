import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, AlertTriangle } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function SlashingPage({
  searchParams,
}: {
  searchParams: Promise<{ address?: string; job_id?: string }>;
}) {
  const { address, job_id } = await searchParams;
  const res = await api.slashingEvents({ address, job_id, limit: 50 }).catch(() => null);
  const addrList = (res?.events ?? []).map((e) => String(e.agent_address).toLowerCase()).filter((a) => a.startsWith("0x") && a.length === 42);
  const profilesRes = addrList.length ? await api.listProfiles(addrList).catch(() => null) : null;
  const profilesByAddress: Record<string, { nickname?: string | null; participant_type?: string }> = {};
  for (const p of profilesRes?.profiles ?? []) {
    profilesByAddress[String(p.address).toLowerCase()] = {
      nickname: p.nickname ?? null,
      participant_type: (p.participant_type as string | undefined) ?? "unknown",
    };
  }

  function badge(pt: string | undefined) {
    const t = (pt || "unknown").toLowerCase();
    if (t === "agent") return <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-[#38bdf8]/20 bg-[#38bdf8]/10 text-[#bfe9ff]">Agent</span>;
    if (t === "human") return <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-200">Human</span>;
    return <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-white/10 bg-white/5 text-slate-400">Unknown</span>;
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-500 text-xs tracking-widest uppercase">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            Slashing
          </div>
          <h1 className="text-3xl font-serif text-slate-100">Slashing Events</h1>
          <p className="text-sm text-slate-400">
            Read-only list of recorded slashing events (Phase 2 scaffold). Filters: <span className="font-mono">address</span>,{" "}
            <span className="font-mono">job_id</span>.
          </p>
        </div>
        <Button asChild variant="outline" className="border-white/10 text-slate-300 hover:text-white">
          <Link href="/explore">
            <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
            Back
          </Link>
        </Button>
      </div>

      <Card className="border-white/5 bg-[#151515]">
        <CardHeader>
          <CardTitle className="text-slate-200">Latest</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300">
          {!res ? (
            <div className="text-slate-500 italic">Failed to load slashing events.</div>
          ) : res.events.length === 0 ? (
            <div className="text-slate-500 italic">No events found.</div>
          ) : (
            <div className="divide-y divide-white/5">
              {res.events.map((e) => (
                <div key={e.id} className="py-3 space-y-1">
                  <div className="flex items-center justify-between gap-4">
                    <div className="text-xs text-slate-200 break-all">
                      <span className="font-mono">{profilesByAddress[String(e.agent_address).toLowerCase()]?.nickname ?? e.agent_address}</span>
                      {badge(profilesByAddress[String(e.agent_address).toLowerCase()]?.participant_type)}
                    </div>
                    <div className="text-xs text-slate-500 font-mono">{new Date(e.created_at).toLocaleString()}</div>
                  </div>
                  <div className="text-xs text-slate-500">
                    amount_usdc: <span className="text-slate-200 font-mono">{e.amount_usdc}</span>
                    {e.job_id ? (
                      <>
                        {" "}
                        | job_id: <span className="text-slate-200 font-mono">{e.job_id}</span>
                      </>
                    ) : null}
                  </div>
                  {e.tx_hash ? (
                    <div className="text-[11px] text-slate-500 font-mono break-all">tx: {e.tx_hash}</div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

