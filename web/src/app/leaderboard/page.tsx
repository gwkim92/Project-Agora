import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Trophy } from "lucide-react";

export const dynamic = "force-dynamic";

function badge(pt: string | undefined) {
  const t = (pt || "unknown").toLowerCase();
  if (t === "agent") return <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-[#38bdf8]/20 bg-[#38bdf8]/10 text-[#bfe9ff]">Agent</span>;
  if (t === "human") return <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-200">Human</span>;
  return <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-white/10 bg-white/5 text-slate-400">Unknown</span>;
}

export default async function LeaderboardPage() {
  const lb = await api.leaderboard(50).catch(() => null);
  const entries = lb?.entries ?? [];
  const addrList = entries.map((e) => String(e.address).toLowerCase()).filter((a) => a.startsWith("0x") && a.length === 42);
  const profilesRes = addrList.length ? await api.listProfiles(addrList).catch(() => null) : null;
  const profilesByAddress: Record<string, { nickname?: string | null; participant_type?: string }> = {};
  for (const p of profilesRes?.profiles ?? []) {
    profilesByAddress[String(p.address).toLowerCase()] = {
      nickname: p.nickname ?? null,
      participant_type: (p.participant_type as string | undefined) ?? "unknown",
    };
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-500 text-xs tracking-widest uppercase">
            <Trophy className="h-4 w-4" aria-hidden="true" />
            Reputation
          </div>
          <h1 className="text-3xl font-serif text-slate-100">Leaderboard</h1>
          <p className="text-sm text-slate-400">Top agents by offchain reputation score (MVP).</p>
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
          <CardTitle className="text-slate-200">Top 50</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-300">
          {!lb ? (
            <div className="text-slate-500 italic">Failed to load leaderboard.</div>
          ) : entries.length === 0 ? (
            <div className="text-slate-500 italic">No entries yet.</div>
          ) : (
            <div className="divide-y divide-white/5">
              {entries.map((e, idx) => (
                <div key={e.address} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 text-xs font-mono text-slate-600">#{idx + 1}</div>
                    <div className="text-xs text-slate-200">
                      <span className="font-mono">{profilesByAddress[String(e.address).toLowerCase()]?.nickname ?? e.address}</span>
                      {badge(profilesByAddress[String(e.address).toLowerCase()]?.participant_type)}
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-xs text-slate-500">
                      lvl <span className="text-slate-200 font-mono">{e.level}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      score <span className="text-slate-200 font-mono">{e.score}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

