import Link from "next/link";
import { api } from "@/lib/api";
import { TOPICS } from "@/lib/topics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowRight, Compass, Filter, Search, Tag } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string }>;
}) {
  const { topic } = await searchParams;
  const selected = topic ? TOPICS.find((t) => t.id === topic) : null;
  const tag = selected?.tags?.[0];

  const jobsRes = await api.listJobs({ tag, status: "open" });

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-100 font-mono uppercase">Terminal / Explore</h1>
          <p className="text-slate-400 mt-1">
            Browse active <span className="text-indigo-400 font-mono">Quests & Bounties</span> from the digital harbor.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="bg-slate-900/50">
            <Filter className="mr-2 h-4 w-4" /> Filter
          </Button>
          <Button asChild size="sm">
            <Link href="/quests/new">New Quest</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Sidebar: Topics */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="border-slate-800/50 bg-slate-950/50">
            <CardHeader className="py-4 border-b border-slate-800/50">
              <CardTitle className="text-xs font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <Tag className="h-3.5 w-3.5" /> Sector Classification
              </CardTitle>
            </CardHeader>
            <CardContent className="p-2 space-y-1">
              <Button 
                asChild 
                variant={!selected ? "secondary" : "ghost"} 
                className="w-full justify-start text-xs font-mono uppercase"
                size="sm"
              >
                <Link href="/explore">All Sectors</Link>
              </Button>
              {TOPICS.map((t) => (
                <Button 
                  key={t.id} 
                  asChild 
                  variant={selected?.id === t.id ? "secondary" : "ghost"} 
                  className="w-full justify-start text-xs font-mono uppercase"
                  size="sm"
                >
                  <Link href={`/explore?topic=${t.id}`}>{t.label}</Link>
                </Button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Main Content: Quest Feed */}
        <div className="lg:col-span-3">
          <Card className="border-slate-800/50 bg-slate-950/50 overflow-hidden">
            <CardHeader className="py-4 bg-slate-900/30 border-b border-slate-800/50 flex flex-row items-center justify-between">
              <div className="space-y-1">
                <CardTitle className="text-sm font-mono uppercase">Quest Feed</CardTitle>
                <CardDescription className="text-[10px] font-mono uppercase tracking-tight">
                  {selected ? `Sector: ${selected.label}` : "Global Stream"} · {jobsRes.jobs.length} Active Nodes
                </CardDescription>
              </div>
              <div className="relative hidden sm:block">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
                <input 
                  type="text" 
                  placeholder="SEARCH ID / TAG..." 
                  className="h-8 w-48 rounded-md border border-slate-800 bg-slate-950 pl-8 text-[10px] font-mono uppercase focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800/50 bg-slate-900/10">
                      <th className="p-4 text-[10px] font-mono uppercase tracking-wider text-slate-500">ID / Created</th>
                      <th className="p-4 text-[10px] font-mono uppercase tracking-wider text-slate-500">Quest Title</th>
                      <th className="p-4 text-[10px] font-mono uppercase tracking-wider text-slate-500 text-right">Bounty (USDC)</th>
                      <th className="p-4 text-[10px] font-mono uppercase tracking-wider text-slate-500 text-center">Status</th>
                      <th className="p-4 w-10"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/30">
                    {jobsRes.jobs.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="p-12 text-center">
                          <div className="text-xs font-mono text-slate-500 uppercase tracking-widest">No active quests found in this sector.</div>
                        </td>
                      </tr>
                    ) : (
                      jobsRes.jobs.map((j) => (
                        <tr key={j.id} className="group hover:bg-indigo-500/5 transition-colors">
                          <td className="p-4 font-mono text-[10px] text-slate-500">
                            <div className="text-slate-400">{j.id.slice(0, 8)}...</div>
                            <div>{new Date(j.created_at).toLocaleDateString()}</div>
                          </td>
                          <td className="p-4">
                            <Link href={`/quests/${j.id}`} className="font-semibold text-slate-200 hover:text-indigo-400 transition-colors line-clamp-1">
                              {j.title}
                            </Link>
                            <div className="flex gap-1 mt-1">
                              {j.tags?.map(tag => (
                                <span key={tag} className="text-[9px] font-mono text-indigo-400/70">#{tag}</span>
                              ))}
                            </div>
                          </td>
                          <td className="p-4 text-right">
                            <span className="font-mono text-emerald-400 font-bold">{j.bounty_usdc}</span>
                          </td>
                          <td className="p-4 text-center">
                            <Badge variant="default" className="text-[9px] h-4 px-1.5 uppercase font-mono border-indigo-500/20">
                              {j.status}
                            </Badge>
                          </td>
                          <td className="p-4 text-right">
                            <Button asChild size="icon" variant="ghost" className="h-7 w-7 text-slate-600 group-hover:text-indigo-400">
                              <Link href={`/quests/${j.id}`}>
                                <ArrowRight className="h-3.5 w-3.5" />
                              </Link>
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
