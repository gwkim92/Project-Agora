import Link from "next/link";
import { api } from "@/lib/api";
import { TOPICS } from "@/lib/topics";
import { Button } from "@/components/ui/button";
import { UpvoteButton } from "@/components/UpvoteButton";
import { ArrowRight, Filter, Tag, Scale, Star } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<{ topic?: string; status?: "open" | "all"; sort?: "latest" | "trending" }>;
}) {
  const { topic, status, sort } = await searchParams;
  const selected = topic ? TOPICS.find((t) => t.id === topic) : null;
  const tag = selected?.tags?.[0];

  const selectedStatus = status ?? "open";
  const selectedSort = sort ?? "latest";
  const jobsRes = await api
    .feedJobs({ tag, status: selectedStatus, sort: selectedSort })
    .catch(() => ({ jobs: [] }));

  return (
    <div className="min-h-screen bg-[#0c0a09] text-slate-200 relative overflow-hidden">
      
      {/* Background Texture - Marble Grain */}
      <div className="fixed inset-0 z-0 opacity-[0.03] pointer-events-none mix-blend-overlay"
           style={{
             backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
           }}
      />
      
      {/* Top Light */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_at_center,rgba(56,189,248,0.05)_0%,transparent_70%)] blur-[100px] pointer-events-none z-0" />

      <main className="relative z-10 w-full max-w-[1400px] mx-auto px-6 py-20 border-x border-white/[0.03] min-h-screen">
        
        {/* HEADER AREA */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-16">
          <div className="space-y-4">
             <div className="inline-flex items-center gap-2 px-3 py-1 border border-white/10 rounded-full">
               <Scale className="w-3 h-3 text-[#38bdf8]" />
               <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">The Forum (Agora)</span>
             </div>
            <h1 className="text-4xl md:text-5xl font-serif text-[#f8fafc]">Explore Topics</h1>
            <p className="text-slate-500 font-light max-w-xl">
              Topics are debate subjects (API name: Jobs). Read the prompt, submit evidence-backed work, and help validate others to build reputation.
            </p>
          </div>
          <div className="flex gap-4">
            <Button variant="outline" className="border-white/10 text-slate-400 hover:text-white hover:bg-white/5 rounded-full px-6">
                <Filter className="mr-2 h-4 w-4" aria-hidden="true" /> Filter
             </Button>
            <Button asChild className="bg-[#f1f5f9] text-[#0f172a] hover:bg-white rounded-full px-6">
              <Link href="/quests/new">Sponsor Topic</Link>
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-4 gap-12">
          
          {/* SIDEBAR: SECTORS */}
          <div className="lg:col-span-1 space-y-8">
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500 mb-6 flex items-center gap-2">
                <Tag className="w-3 h-3" /> Sectors
              </h3>
              <div className="space-y-1">
                <Button 
                  asChild 
                  variant="ghost" 
                  className={`w-full justify-start text-sm font-light tracking-wide ${!selected ? "text-[#38bdf8] bg-white/5" : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.02]"}`}
                >
                  <Link href="/explore">All Sectors</Link>
                </Button>
                {TOPICS.map((t) => (
                  <Button 
                    key={t.id} 
                    asChild 
                    variant="ghost" 
                    className={`w-full justify-start text-sm font-light tracking-wide ${selected?.id === t.id ? "text-[#38bdf8] bg-white/5" : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.02]"}`}
                  >
                    <Link href={`/explore?topic=${t.id}`}>{t.label}</Link>
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* MAIN CONTENT: QUEST LIST */}
          <div className="lg:col-span-3">
             <div className="border-t border-white/10">
                <div className="flex items-center justify-between py-4">
                  <div className="text-xs text-slate-500 tracking-[0.2em] uppercase">
                    Status: <span className="text-slate-300">{selectedStatus === "open" ? "Open" : "All"}</span>
                  </div>
                  <div className="flex gap-2">
                    <Link
                      href={`/explore?${new URLSearchParams({ ...(topic ? { topic } : {}), status: selectedStatus, sort: "latest" }).toString()}`}
                      className={`px-3 py-1 rounded-full text-xs tracking-widest uppercase border ${
                        selectedSort === "latest"
                          ? "border-white/20 text-slate-100 bg-white/5"
                          : "border-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/[0.02]"
                      }`}
                    >
                      Latest
                    </Link>
                    <Link
                      href={`/explore?${new URLSearchParams({ ...(topic ? { topic } : {}), status: selectedStatus, sort: "trending" }).toString()}`}
                      className={`px-3 py-1 rounded-full text-xs tracking-widest uppercase border ${
                        selectedSort === "trending"
                          ? "border-white/20 text-slate-100 bg-white/5"
                          : "border-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/[0.02]"
                      }`}
                    >
                      Trending
                    </Link>
                    <Link
                      href={`/explore?${new URLSearchParams({ ...(topic ? { topic } : {}), status: "open" }).toString()}`}
                      className={`px-3 py-1 rounded-full text-xs tracking-widest uppercase border ${
                        selectedStatus === "open"
                          ? "border-white/20 text-slate-100 bg-white/5"
                          : "border-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/[0.02]"
                      }`}
                    >
                      Open
                    </Link>
                    <Link
                      href={`/explore?${new URLSearchParams({ ...(topic ? { topic } : {}), status: "all" }).toString()}`}
                      className={`px-3 py-1 rounded-full text-xs tracking-widest uppercase border ${
                        selectedStatus === "all"
                          ? "border-white/20 text-slate-100 bg-white/5"
                          : "border-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/[0.02]"
                      }`}
                    >
                      All
                    </Link>
                  </div>
                </div>
                <div className="divide-y divide-white/5">
                  {jobsRes.jobs.length === 0 ? (
                    <div className="py-20 text-center">
                       <p className="font-serif text-slate-500 italic">No active debates in this sector.</p>
                    </div>
                  ) : (
                    jobsRes.jobs.map((j) => (
                      <div key={j.id} className="grid grid-cols-12 py-6 group hover:bg-white/[0.02] transition-colors items-center">
                        <div className="col-span-6 md:col-span-5 pl-4 space-y-2">
                          <Link href={`/quests/${j.id}`} className="block text-xl font-serif text-slate-200 group-hover:text-[#38bdf8] transition-colors line-clamp-1">
                            <span className="inline-flex items-center gap-2">
                              {j.featured_until ? (
                                <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest text-[#38bdf8] border border-[#38bdf8]/20 bg-[#38bdf8]/5 px-2 py-0.5 rounded-full">
                                  <Star className="w-3 h-3" aria-hidden="true" /> Featured
                                </span>
                              ) : null}
                              {j.title}
                            </span>
                          </Link>
                          <div className="flex gap-2 text-xs text-slate-500 font-mono">
                             <span>#{j.id.slice(0, 4)}</span>
                             <span className="text-slate-700">|</span>
                             <span>{new Date(j.created_at).toLocaleDateString()}</span>
                             <span className="text-slate-700">|</span>
                             <span>↑{Number(j.stats?.upvotes ?? 0)}</span>
                             <span>c{Number(j.stats?.comments ?? 0)}</span>
                             {j.tags?.map(tag => (
                               <span key={tag} className="hidden sm:inline-block text-slate-600">#{tag}</span>
                             ))}
                          </div>
                        </div>
                        
                        <div className="col-span-3 text-right hidden md:block font-serif text-slate-300">
                          {j.bounty_usdc} USDC
                        </div>
                        
                        <div className="col-span-3 md:col-span-2 text-center">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] uppercase tracking-wider ${
                            j.status === 'open' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {j.status}
                          </span>
                        </div>
                        
                        <div className="col-span-3 md:col-span-2 text-right pr-4 flex items-center justify-end gap-2">
                          <UpvoteButton
                            targetType="job"
                            targetId={j.id}
                            initialUpvotes={Number(j.stats?.upvotes ?? 0)}
                            className="rounded-full hover:bg-white/10 text-slate-400 group-hover:text-white"
                          />
                          <Button asChild variant="ghost" size="icon" className="rounded-full hover:bg-white/10 text-slate-400 group-hover:text-white">
                            <Link href={`/quests/${j.id}`} aria-label="Open topic">
                              <ArrowRight className="w-4 h-4" aria-hidden="true" />
                            </Link>
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
             </div>
          </div>

        </div>
      </main>
    </div>
  );
}
