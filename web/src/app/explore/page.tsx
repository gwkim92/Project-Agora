import Link from "next/link";
import { api } from "@/lib/api";
import { TOPICS } from "@/lib/topics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowRight, Compass } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string }>;
}) {
  const { topic } = await searchParams;
  const selected = topic ? TOPICS.find((t) => t.id === topic) : null;
  const tag = selected?.tags?.[0]; // MVP: topic 대표 tag 1개로 필터

  const jobsRes = await api.listJobs({ tag, status: "open" });

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-100">Explore</h1>
          <p className="text-slate-400 mt-1">
            지금 참여 가능한 <span className="text-indigo-300">퀘스트(바운티)</span>를 주제별로 탐색합니다.
          </p>
        </div>
        <Button asChild>
          <Link href="/quests/new">퀘스트 만들기</Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="border-b border-slate-800/50 pb-4">
          <CardTitle className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-indigo-400" />
            Topics
          </CardTitle>
          <CardDescription>주제를 선택하면 관련 퀘스트만 보여줍니다.</CardDescription>
        </CardHeader>
        <CardContent className="pt-6 flex flex-wrap gap-2">
          <Button asChild variant={selected ? "outline" : "default"} size="sm">
            <Link href="/explore">전체</Link>
          </Button>
          {TOPICS.map((t) => (
            <Button key={t.id} asChild variant={selected?.id === t.id ? "default" : "outline"} size="sm">
              <Link href={`/explore?topic=${t.id}`}>{t.label}</Link>
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card className="h-fit">
        <CardHeader className="border-b border-slate-800/50 pb-4">
          <CardTitle>Open Quests</CardTitle>
          <CardDescription>
            {selected ? `${selected.label} 주제` : "전체"} · {jobsRes.jobs.length}개
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-800/50">
            {jobsRes.jobs.length === 0 ? (
              <div className="flex h-[260px] flex-col items-center justify-center text-center p-8">
                <div className="text-sm text-slate-400">해당 주제의 열린 퀘스트가 없습니다.</div>
                <div className="mt-4">
                  <Button asChild>
                    <Link href="/quests/new">퀘스트 만들기</Link>
                  </Button>
                </div>
              </div>
            ) : (
              jobsRes.jobs.map((j) => (
                <div key={j.id} className="flex items-center justify-between p-4 hover:bg-slate-800/30 transition-colors group">
                  <div className="space-y-1.5 min-w-0 pr-4">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/quests/${j.id}`}
                        className="font-semibold text-slate-200 hover:text-indigo-400 transition-colors truncate"
                      >
                        {j.title}
                      </Link>
                      <Badge variant="default" className="uppercase text-[10px] tracking-wide">
                        open
                      </Badge>
                    </div>
                    <div className="text-xs text-slate-500 font-mono flex items-center gap-3">
                      <span className="truncate">{j.id}</span>
                      <span className="w-1 h-1 rounded-full bg-slate-700" />
                      <span>{new Date(j.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right hidden sm:block">
                      <div className="text-sm font-medium text-emerald-400 font-mono">{j.bounty_usdc} USDC</div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider">Bounty</div>
                    </div>
                    <Button asChild size="icon" variant="ghost" className="h-8 w-8 text-slate-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10">
                      <Link href={`/quests/${j.id}`}>
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

