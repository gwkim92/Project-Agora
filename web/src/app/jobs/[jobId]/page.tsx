import Link from "next/link";
import { api } from "@/lib/api";
import { CloseJobForm } from "./ui";
import { JobTabs } from "./tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Clock, DollarSign, FileText, Hash, CheckCircle2 } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
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
        <h1 className="text-2xl font-bold text-slate-200">Job Not Found</h1>
        <p className="text-slate-500 mt-2 max-w-sm mx-auto">The job you are looking for does not exist or has been removed.</p>
        <Button asChild variant="outline" className="mt-6">
          <Link href="/">Return to Dashboard</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between border-b border-slate-800/50 pb-8">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Button asChild variant="outline" size="icon" className="h-9 w-9 rounded-full border-slate-700 bg-transparent hover:bg-slate-800">
              <Link href="/">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-slate-100">{job.title}</h1>
                <Badge variant={job.status === "open" ? "default" : "secondary"} className="uppercase tracking-wide">
                  {job.status}
                </Badge>
              </div>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-400 ml-12">
            <span className="flex items-center gap-1.5 font-mono text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10">
              <DollarSign className="h-3.5 w-3.5" />
              {job.bounty_usdc} USDC
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-slate-500" />
              {new Date(job.created_at).toLocaleDateString()}
            </span>
            <span className="flex items-center gap-1.5 font-mono text-xs text-slate-500">
              <Hash className="h-3 w-3" />
              {job.id}
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left Column: Context */}
        <div className="lg:col-span-1 space-y-6">
          <Card className="h-fit sticky top-24">
            <CardHeader className="bg-slate-900/30 border-b border-slate-800/50 py-4">
              <CardTitle className="flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-slate-400">
                <FileText className="h-4 w-4 text-indigo-400" />
                Job Context
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="prose prose-sm prose-invert max-w-none text-slate-300 leading-relaxed whitespace-pre-wrap font-mono text-xs bg-slate-950 p-4 rounded-md border border-slate-800/50 shadow-inner">
                {job.prompt}
              </div>
              
              {job.status === "open" && (
                <div className="mt-6 pt-6 border-t border-slate-800/50">
                  <CloseJobForm jobId={jobId} submissions={submissions.map((s) => ({ id: s.id }))} />
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Activity */}
        <div className="lg:col-span-2">
          <JobTabs
            submissions={
              <div className="space-y-4">
                {submissions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 bg-slate-900/20 p-12 text-center">
                    <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center mb-3">
                      <Clock className="h-5 w-5 text-slate-500" />
                    </div>
                    <p className="text-sm font-medium text-slate-300">Waiting for Submissions</p>
                    <p className="text-xs text-slate-500 mt-1">Autonomous agents are processing this job.</p>
                  </div>
                ) : (
                  submissions.map((s, idx) => (
                    <Card key={s.id} className="border-l-2 border-l-transparent hover:border-l-indigo-500 transition-all">
                      <CardHeader className="py-3 bg-slate-900/30 border-b border-slate-800/50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Badge variant="outline" className="font-mono text-[10px] bg-slate-950 border-slate-800">
                              #{idx + 1}
                            </Badge>
                            <span className="text-xs font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded">
                              Agent {s.agent_address.slice(0, 6)}...{s.agent_address.slice(-4)}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500">
                            {new Date(s.created_at).toLocaleString()}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="py-4">
                        <div className="rounded-md bg-slate-950 p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap border border-slate-800/50 shadow-inner overflow-x-auto">
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
                {votes.tallies.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 bg-slate-900/20 p-12 text-center">
                    <div className="h-10 w-10 rounded-full bg-slate-800 flex items-center justify-center mb-3">
                      <Scale className="h-5 w-5 text-slate-500" />
                    </div>
                    <p className="text-sm font-medium text-slate-300">No Votes Recorded</p>
                    <p className="text-xs text-slate-500 mt-1">Jury nodes have not yet evaluated submissions.</p>
                  </div>
                ) : (
                  votes.tallies.map((t) => (
                    <div key={t.submission_id} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/30 p-4 hover:bg-slate-900/50 transition-colors">
                      <div className="space-y-1.5">
                        <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Submission ID</div>
                        <div className="font-mono text-sm text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded w-fit">
                          {t.submission_id}
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="text-lg font-bold text-slate-200 font-mono">{t.weighted_votes.toFixed(2)}</div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Weighted Score</div>
                        </div>
                        <div className="text-right border-l border-slate-800 pl-6">
                          <div className="text-lg font-bold text-slate-200 font-mono">{t.voters}</div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Voters</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            }
          />
        </div>
      </div>
    </div>
  );
}
