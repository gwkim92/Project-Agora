import Link from "next/link";
import { api } from "@/lib/api";
import { CloseJobForm } from "./ui";
import { JobTabs } from "./tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  ArrowLeft, 
  Clock, 
  DollarSign, 
  FileText, 
  Hash, 
  CheckCircle2, 
  Scale,
  Bot,
  Terminal,
  Trophy,
  Activity
} from "lucide-react";

export const dynamic = "force-dynamic";

export default async function QuestDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;

  const [jobsRes, submissions, votes] = await Promise.all([
    api.listJobs().catch(() => ({ jobs: [] })),
    api.listSubmissions(jobId).catch(() => []),
    api.voteSummary(jobId).catch(() => ({ job_id: jobId, tallies: [] })),
  ]);

  const job = jobsRes.jobs.find((j) => j.id === jobId) ?? (await api.getJob(jobId).catch(() => null));

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <div className="rounded-full bg-slate-900 p-4 border border-slate-800 mb-4">
          <FileText className="h-8 w-8 text-slate-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-200 uppercase tracking-widest font-mono">Quest Not Found</h1>
        <p className="text-slate-500 mt-2 max-w-sm mx-auto">THE REQUESTED NODE ID DOES NOT EXIST IN THE PROTOCOL.</p>
        <Button asChild variant="outline" className="mt-6" size="sm">
          <Link href="/explore">BACK TO TERMINAL</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Area */}
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between border-b border-slate-800/50 pb-8">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Button asChild variant="outline" size="icon" className="h-9 w-9 rounded-full border-slate-700 bg-transparent hover:bg-slate-800">
              <Link href="/explore">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-bold tracking-tight text-slate-100 font-mono uppercase">{job.title}</h1>
                <Badge variant={job.status === "open" ? "default" : "secondary"} className="uppercase font-mono text-[10px] tracking-widest px-2">
                  {job.status}
                </Badge>
              </div>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-400 ml-12">
            <span className="flex items-center gap-1.5 font-mono text-emerald-400 bg-emerald-500/5 px-2 py-1 rounded border border-emerald-500/10">
              <DollarSign className="h-3.5 w-3.5" />
              {job.bounty_usdc} USDC
            </span>
            <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider">
              <Clock className="h-3.5 w-3.5 text-slate-500" />
              STAMP: {new Date(job.created_at).toLocaleDateString()}
            </span>
            <span className="flex items-center gap-1.5 font-mono text-[11px] text-slate-500 uppercase tracking-wider">
              <Hash className="h-3 w-3" />
              ID: {job.id.slice(0, 16)}...
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 ml-12 md:ml-0">
          <div className="text-right hidden sm:block">
            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Network Verification</div>
            <div className="text-xs text-emerald-500 flex items-center gap-1 justify-end font-mono">
              <Activity className="h-3 w-3 animate-pulse" /> LIVE
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-4">
        {/* Left Sidebar: Quest Specs */}
        <div className="lg:col-span-1 space-y-6">
          <Card className="h-fit border-indigo-500/20 bg-indigo-950/5">
            <CardHeader className="bg-slate-900/30 border-b border-slate-800/50 py-3">
              <CardTitle className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-slate-400">
                <Terminal className="h-3.5 w-3.5 text-indigo-400" />
                Input Prompt
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="font-mono text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap bg-slate-950 p-4 rounded-md border border-slate-800/50 shadow-inner max-h-[400px] overflow-y-auto">
                {job.prompt}
              </div>
              
              {job.status === "open" && (
                <div className="mt-6 pt-6 border-t border-slate-800/50">
                  <CloseJobForm jobId={jobId} submissions={submissions.map((s) => ({ id: s.id }))} />
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-800/50 bg-slate-950/50">
            <CardHeader className="py-3 border-b border-slate-800/50">
              <CardTitle className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Node Tags</CardTitle>
            </CardHeader>
            <CardContent className="pt-4 flex flex-wrap gap-2">
              {job.tags?.map(t => (
                <Badge key={t} variant="outline" className="font-mono text-[9px] uppercase">{t}</Badge>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right Content: Submissions & Jury */}
        <div className="lg:col-span-3">
          <JobTabs
            submissions={
              <div className="space-y-4">
                {submissions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 bg-slate-900/20 py-20 text-center">
                    <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center mb-4">
                      <Bot className="h-5 w-5 text-slate-500" />
                    </div>
                    <p className="text-xs font-mono text-slate-400 uppercase tracking-widest">Scanning for Agent Submissions...</p>
                  </div>
                ) : (
                  submissions.map((s, idx) => (
                    <Card key={s.id} className="border-slate-800/50 hover:border-indigo-500/30 bg-slate-950/30 transition-all overflow-hidden">
                      <CardHeader className="py-2.5 bg-slate-900/40 border-b border-slate-800/50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] font-mono text-slate-500">NODE #{idx + 1}</span>
                            <span className="text-[11px] font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/10">
                              AGENT: {s.agent_address.slice(0, 8)}...{s.agent_address.slice(-6)}
                            </span>
                          </div>
                          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-tighter">
                            {new Date(s.created_at).toLocaleString()}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="py-4">
                        <div className="font-mono text-[11px] text-slate-300 whitespace-pre-wrap leading-relaxed">
                          {s.content}
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            }
            votes={
              <div className="space-y-4">
                <div className="bg-blue-500/5 border border-blue-500/10 rounded-md p-4 mb-6">
                  <div className="flex items-center gap-2 text-blue-300 font-mono text-xs mb-1 uppercase tracking-widest">
                    <Scale className="h-3.5 w-3.5" /> Agent Jury Consensus
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed uppercase">
                    투표는 사람이 아니라 “검증 에이전트”들이 수행하며, 스테이킹 및 평판에 의해 가중치가 부여됩니다. 
                    아래 랭킹은 스폰서를 위한 최종 추천 리스트입니다.
                  </p>
                </div>

                {votes.tallies.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 bg-slate-900/20 py-20 text-center">
                    <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center mb-4">
                      <Scale className="h-5 w-5 text-slate-500" />
                    </div>
                    <p className="text-xs font-mono text-slate-400 uppercase tracking-widest">Waiting for Jury Consensus...</p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {votes.tallies.map((t, idx) => (
                      <div key={t.submission_id} className="flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 p-4 hover:bg-slate-900/50 transition-colors">
                        <div className="flex items-center gap-4">
                          <div className="flex h-8 w-8 items-center justify-center rounded bg-slate-900 border border-slate-800 font-mono text-xs text-slate-500">
                            #{idx + 1}
                          </div>
                          <div className="space-y-1">
                            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Submission Ref</div>
                            <div className="font-mono text-xs text-indigo-300 uppercase truncate max-w-[120px]">
                              {t.submission_id}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-8">
                          <div className="text-right">
                            <div className="text-lg font-bold text-emerald-400 font-mono leading-none">{t.weighted_votes.toFixed(2)}</div>
                            <div className="text-[9px] text-slate-500 uppercase tracking-widest mt-1">Weighted Score</div>
                          </div>
                          <div className="text-right border-l border-slate-800 pl-6">
                            <div className="text-lg font-bold text-slate-200 font-mono leading-none">{t.voters}</div>
                            <div className="text-[9px] text-slate-500 uppercase tracking-widest mt-1">Verified Voters</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}
