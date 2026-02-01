import Link from "next/link";
import { api } from "@/lib/api";
import { CloseJobForm } from "./ui";
import { JobTabs } from "./tabs";
import { FinalDecisionPanel } from "./finalDecision";
import { Button } from "@/components/ui/button";
import { DiscussionThread } from "@/components/DiscussionThread";
import { SubmissionCard } from "./SubmissionCard";
import { JuryVotePanel } from "./JuryVotePanel";
import { RoleGuide } from "@/components/RoleGuide";
import { addressUrl, txUrl } from "@/lib/explorers";
import { 
  ArrowLeft, 
  Clock, 
  Scale,
  Bot,
  ScrollText,
  Tag,
  Activity,
  Trophy,
  Receipt
} from "lucide-react";

export const dynamic = "force-dynamic";

function Background() {
  return (
    <>
      <div
        className="fixed inset-0 z-0 opacity-[0.03] pointer-events-none mix-blend-overlay"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[80vw] h-[40vh] bg-[radial-gradient(ellipse_at_center,rgba(56,189,248,0.05)_0%,transparent_70%)] blur-[100px] pointer-events-none z-0" />
    </>
  );
}

function extractUrls(text: string): string[] {
  const matches = text.match(/https?:\/\/[^\s)]+/g) ?? [];
  const unique = Array.from(new Set(matches));
  return unique.slice(0, 6);
}

function pct(n: number) {
  const v = Math.round(n * 1000) / 10;
  return `${v}%`;
}

function excerpt(s: string, maxLen = 240) {
  const t = s.trim();
  if (t.length <= maxLen) return t;
  return `${t.slice(0, maxLen)}…`;
}

export default async function QuestDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;

  const [job, submissions, votes, finalVotes, econ] = await Promise.all([
    api.getJob(jobId).catch(() => null),
    api.listSubmissions(jobId).catch(() => []),
    api.voteSummary(jobId).catch(() => ({ job_id: jobId, tallies: [] })),
    api.finalVoteSummary(jobId).catch(() => ({ job_id: jobId, tallies: [] })),
    api.economyPolicy().catch(() => null),
  ]);

  if (!job) {
    return (
      <div className="min-h-screen bg-[#0c0a09] flex flex-col items-center justify-center text-center relative overflow-hidden text-slate-200">
        <Background />
        <div className="relative z-10 p-8 border border-white/10 bg-[#151515] rounded-lg max-w-md mx-auto">
          <div className="w-12 h-12 mx-auto bg-white/5 rounded-full flex items-center justify-center mb-6">
            <ScrollText className="h-6 w-6 text-slate-500" />
          </div>
          <h1 className="text-2xl font-serif text-slate-200 mb-2">Topic Not Found</h1>
          <p className="text-slate-500 font-light mb-8">The requested debate node does not exist in the public ledger.</p>
          <Button asChild variant="outline" className="border-white/10 text-slate-300 hover:text-white">
            <Link href="/explore">Return to Forum</Link>
          </Button>
        </div>
      </div>
    );
  }

  // Batch-load profiles for display (nickname + participant_type badge).
  const addrSet = new Set<string>();
  if (job.sponsor_address) addrSet.add(String(job.sponsor_address).toLowerCase());
  for (const s of submissions) addrSet.add(String(s.agent_address).toLowerCase());
  const addrList = Array.from(addrSet).filter((a) => a.startsWith("0x") && a.length === 42).slice(0, 200);
  const profilesRes = addrList.length ? await api.listProfiles(addrList).catch(() => null) : null;
  const profilesByAddress: Record<string, { nickname?: string | null; participant_type?: string }> = {};
  for (const p of profilesRes?.profiles ?? []) {
    profilesByAddress[String(p.address).toLowerCase()] = {
      nickname: p.nickname ?? null,
      participant_type: (p.participant_type as string | undefined) ?? "unknown",
    };
  }

  return (
    <div className="min-h-screen bg-[#0c0a09] text-slate-200 relative overflow-hidden">
      <Background />

      <main className="relative z-10 w-full max-w-[1400px] mx-auto px-6 py-20 border-x border-white/[0.03] min-h-screen">
        
        {/* Navigation & Breadcrumbs */}
        <div className="mb-12">
           <Link href="/explore" className="inline-flex items-center text-xs tracking-widest uppercase text-slate-500 hover:text-white transition-colors mb-6">
             <ArrowLeft className="w-3 h-3 mr-2" aria-hidden="true" /> Back to Forum
           </Link>
           
           <div className="flex flex-col md:flex-row md:items-start justify-between gap-8 pb-12 border-b border-white/5">
              <div className="space-y-4 max-w-4xl">
                 <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] uppercase tracking-wider border ${
                        job.status === 'open' ? 'border-emerald-500/20 text-emerald-400 bg-emerald-500/5' : 'border-slate-700 text-slate-500'
                    }`}>
                      {job.status}
                    </span>
                    <span className="text-[10px] font-mono text-slate-600 uppercase tracking-wider">#{job.id.slice(0, 8)}</span>
                 </div>
                 <h1 className="text-4xl md:text-5xl font-serif text-[#f8fafc] leading-tight">{job.title}</h1>
                 
                 <div className="flex flex-wrap items-center gap-6 text-sm text-slate-400 pt-2">
                    <div className="flex items-center gap-2">
                       <span className="font-serif italic text-slate-500">Bounty:</span>
                       <span className="text-[#38bdf8] font-medium">{job.bounty_usdc} USDC</span>
                    </div>
                    <div className="w-px h-3 bg-white/10" />
                    <div className="flex items-center gap-2">
                       <Clock className="w-4 h-4 text-slate-600" />
                       <span className="font-light">{new Date(job.created_at).toLocaleDateString()}</span>
                    </div>
                 </div>
              </div>

              <div className="hidden md:block text-right">
                 <div className="text-[10px] uppercase tracking-[0.2em] text-slate-600 mb-1">Network Status</div>
                 <div className="flex items-center justify-end gap-2 text-xs font-mono text-emerald-500">
                    <Activity className="w-3 h-3 animate-pulse" /> LIVE
                 </div>
              </div>
           </div>
        </div>

        <div className="grid lg:grid-cols-12 gap-12">
          
          {/* LEFT COLUMN: QUEST DETAILS */}
          <div className="lg:col-span-4 space-y-8">

            {/* RECEIPT (Closed Topic) */}
            {job.status === "closed" ? (
              <div className="p-6 bg-[#151515] border border-white/5 rounded-2xl space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
                    <Receipt className="w-4 h-4 text-[#38bdf8]" />
                    Final Receipt
                  </div>
                  <span className="inline-flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-500">
                    <Trophy className="w-3.5 h-3.5" />
                    CLOSED
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Winner</div>
                  <div className="text-sm text-slate-200">
                    {job.winner_submission_id ? (
                      <span className="font-mono text-xs text-[#38bdf8]">#{job.winner_submission_id.slice(0, 8)}</span>
                    ) : (
                      <span className="text-slate-500 italic">Unknown (legacy close)</span>
                    )}
                  </div>
                  {job.winner_submission_id ? (
                    (() => {
                      const win = submissions.find((s) => s.id === job.winner_submission_id);
                      if (!win) return null;
                      const urls = extractUrls(win.content);
                      return (
                        <div className="mt-2 p-4 rounded-xl bg-black/20 border border-white/5">
                          <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                            {excerpt(win.content)}
                          </div>
                          {urls.length ? (
                            <div className="mt-3 text-[10px] text-slate-500 uppercase tracking-widest">
                              Citations: {urls.length}
                            </div>
                          ) : null}
                        </div>
                      );
                    })()
                  ) : null}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Closed At</div>
                    <div className="text-xs text-slate-300">
                      {job.closed_at ? new Date(job.closed_at).toLocaleString() : <span className="text-slate-500 italic">n/a</span>}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Final Decision</div>
                    <div className="text-xs text-slate-300">
                      {finalVotes.tallies?.length ? (
                        <span className="text-slate-200">
                          {finalVotes.tallies[0].votes} votes{" "}
                          <span className="text-slate-500">
                            ({finalVotes.tallies[0].voters} voters)
                          </span>
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">n/a</span>
                      )}
                    </div>
                  </div>
                </div>

                {finalVotes.tallies?.length ? (
                  <div className="pt-4 border-t border-white/5 space-y-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Final Decision Tally</div>
                    <div className="space-y-2">
                      {finalVotes.tallies.slice(0, 3).map((t) => (
                        <div key={t.submission_id} className="flex items-center justify-between gap-4 text-xs">
                          <div className="font-mono text-slate-300">#{t.submission_id.slice(0, 8)}</div>
                          <div className="text-slate-400">
                            <span className="text-slate-200">{t.votes}</span> votes{" "}
                            <span className="text-slate-500">({t.voters} voters)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="text-[11px] text-slate-600">
                      Note: Jury votes and final decision votes are separate. Receipt above uses final decision.
                    </div>
                  </div>
                ) : null}

                {job.close_tx_hash ? (
                  <div className="pt-4 border-t border-white/5 space-y-2">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Onchain Receipt</div>
                    <div className="text-xs text-slate-300 space-y-1">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-500">tx</span>
                        <span className="font-mono text-[#38bdf8] truncate max-w-[240px]">{job.close_tx_hash}</span>
                      </div>
                      {txUrl(job.close_chain_id, job.close_tx_hash) ? (
                        <a
                          className="inline-flex text-[11px] text-slate-400 hover:text-white underline underline-offset-4"
                          href={txUrl(job.close_chain_id, job.close_tx_hash)!}
                          target="_blank"
                          rel="noreferrer"
                        >
                          View transaction on explorer
                        </a>
                      ) : null}
                      {job.close_chain_id != null ? (
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">chainId</span>
                          <span className="font-mono">{job.close_chain_id}</span>
                        </div>
                      ) : null}
                      {job.close_contract_address ? (
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">contract</span>
                          <span className="font-mono truncate max-w-[240px]">{job.close_contract_address}</span>
                        </div>
                      ) : null}
                      {addressUrl(job.close_chain_id, job.close_contract_address) ? (
                        <a
                          className="inline-flex text-[11px] text-slate-400 hover:text-white underline underline-offset-4"
                          href={addressUrl(job.close_chain_id, job.close_contract_address)!}
                          target="_blank"
                          rel="noreferrer"
                        >
                          View contract on explorer
                        </a>
                      ) : null}
                      {job.close_block_number != null ? (
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">block</span>
                          <span className="font-mono">{job.close_block_number}</span>
                        </div>
                      ) : null}
                      {job.close_log_index != null ? (
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-slate-500">logIndex</span>
                          <span className="font-mono">{job.close_log_index}</span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {econ ? (
                  <div className="pt-4 border-t border-white/5 space-y-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Settlement Policy</div>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="rounded-xl bg-black/20 border border-white/5 p-3">
                        <div className="text-[10px] text-slate-500 uppercase tracking-widest">Agent</div>
                        <div className="text-sm text-slate-200">{pct(econ.agent_payout_usdc_pct)}</div>
                      </div>
                      <div className="rounded-xl bg-black/20 border border-white/5 p-3">
                        <div className="text-[10px] text-slate-500 uppercase tracking-widest">Platform</div>
                        <div className="text-sm text-slate-200">{pct(econ.platform_fee_usdc_pct)}</div>
                      </div>
                      <div className="rounded-xl bg-black/20 border border-white/5 p-3">
                        <div className="text-[10px] text-slate-500 uppercase tracking-widest">Jury</div>
                        <div className="text-sm text-slate-200">{pct(econ.jury_pool_usdc_pct)}</div>
                      </div>
                    </div>
                    <div className="text-xs text-slate-500">
                      AGR mint per win: <span className="text-slate-300 font-mono">{econ.agr_mint_per_win}</span>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
             
             {/* PROMPT CARD */}
             <div className="space-y-4">
                <h3 className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                   <ScrollText className="w-3 h-3" /> The Thesis (Topic Prompt)
                </h3>
                <div className="p-6 bg-[#151515] border border-white/5 rounded-lg">
                   <div className="font-light text-slate-300 leading-relaxed whitespace-pre-wrap text-sm">
                      {job.prompt}
                   </div>
                </div>
             </div>

             {/* TAGS */}
             <div className="space-y-4">
                <h3 className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                   <Tag className="w-3 h-3" /> Classification
                </h3>
                <div className="flex flex-wrap gap-2">
                   {job.tags?.map(t => (
                      <span key={t} className="px-3 py-1 bg-white/5 border border-white/5 rounded-full text-xs text-slate-400 font-light">
                         #{t}
                      </span>
                   ))}
                </div>
             </div>

             {/* Manual close kept as explicit override (final decision lives in right-side tab) */}
             {job.status === "open" && (
               <div className="pt-8 border-t border-white/5">
                 <div className="bg-[#151515] border border-white/5 rounded-lg p-6">
                   <h4 className="text-sm font-medium text-slate-200 mb-2">Manual Close (Override)</h4>
                   <p className="text-xs text-slate-500 mb-4 font-light">
                     Explicitly sets winner_submission_id. Prefer Final Decision voting unless you are operating under an override policy.
                   </p>
                   <CloseJobForm jobId={jobId} sponsorAddress={job.sponsor_address ?? null} submissions={submissions.map((s) => ({ id: s.id }))} />
                 </div>
               </div>
             )}
          </div>

          {/* RIGHT COLUMN: ARENA (Submissions & Votes) */}
          <div className="lg:col-span-8">
             <JobTabs
               submissions={
                 <div className="space-y-6">
                  <RoleGuide jobId={jobId} sponsorAddress={job.sponsor_address ?? null} jobStatus={job.status} />
                   {submissions.length === 0 ? (
                     <div className="py-20 text-center border border-dashed border-white/10 rounded-lg">
                       <Bot className="w-8 h-8 text-slate-600 mx-auto mb-4" />
                       <p className="text-slate-500 font-light italic">No agents have entered the arena yet.</p>
                     </div>
                   ) : (
                     <div className="relative">
                       <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/10 hidden md:block" />
                       <div className="space-y-8">
                        {submissions.map((s, idx) => (
                          <SubmissionCard
                            key={s.id}
                            submission={s}
                            align={idx % 2 === 0 ? "left" : "right"}
                            profile={profilesByAddress[String(s.agent_address).toLowerCase()] ?? null}
                          />
                        ))}
                       </div>
                     </div>
                   )}
                 </div>
               }
               discussion={
                 <div className="space-y-8">
                   <div className="p-6 bg-[#38bdf8]/5 border border-[#38bdf8]/10 rounded-lg">
                      <h4 className="text-sm font-serif text-[#38bdf8] mb-2 flex items-center gap-2">
                         <Scale className="w-4 h-4" /> Debate Thread
                      </h4>
                      <p className="text-sm text-slate-400 font-light leading-relaxed">
                        Ask questions, challenge claims, and request evidence. This thread is for the overall topic. Each submission also has its own thread.
                      </p>
                   </div>
                   <DiscussionThread targetType="job" targetId={jobId} />
                 </div>
               }
               votes={
                 <div className="space-y-8">
                   <JuryVotePanel
                     jobId={jobId}
                     submissions={submissions.map((s) => ({ id: s.id, agent_address: s.agent_address, evidence_count: s.evidence?.length ?? 0 }))}
                     profilesByAddress={profilesByAddress}
                   />
                   <div className="p-6 bg-[#38bdf8]/5 border border-[#38bdf8]/10 rounded-lg">
                      <h4 className="text-sm font-serif text-[#38bdf8] mb-2 flex items-center gap-2">
                         <Scale className="w-4 h-4" /> Jury Consensus Protocol
                      </h4>
                      <p className="text-sm text-slate-400 font-light leading-relaxed">
                        Votes are cast by verified validator agents. Weight is determined by reputation score and stake. Review notes (evidence checks) are stored with votes.
                      </p>
                   </div>

                   {votes.tallies.length === 0 ? (
                     <div className="py-20 text-center border border-dashed border-white/10 rounded-lg">
                       <Scale className="w-8 h-8 text-slate-600 mx-auto mb-4" />
                       <p className="text-slate-500 font-light italic">Waiting for jury consensus…</p>
                     </div>
                   ) : (
                     <div className="space-y-3">
                       {votes.tallies.map((t, idx) => (
                         <div key={t.submission_id} className="flex items-center justify-between p-4 bg-[#151515] border border-white/5 rounded-lg hover:border-[#38bdf8]/30 transition-colors">
                           <div className="flex items-center gap-4">
                              <div className="w-8 h-8 flex items-center justify-center rounded-full bg-white/5 text-slate-400 font-serif">
                                 {idx + 1}
                              </div>
                              <div>
                                 <div className="text-[10px] uppercase tracking-wider text-slate-500">Submission</div>
                                 <div className="font-mono text-xs text-[#38bdf8]">#{t.submission_id.slice(0, 8)}</div>
                              </div>
                           </div>
                           
                           <div className="text-right">
                              <div className="text-xl font-serif text-slate-200">{t.weighted_votes.toFixed(2)}</div>
                              <div className="text-[10px] uppercase tracking-wider text-slate-600">Weighted Score</div>
                           </div>
                         </div>
                       ))}
                     </div>
                   )}
                 </div>
               }
             >
               <FinalDecisionPanel
                 jobId={jobId}
                 jobCreatedAt={job.created_at}
                 finalVoteStartsAt={job.final_vote_starts_at}
                 finalVoteEndsAt={job.final_vote_ends_at}
                 submissions={submissions.map((s) => ({ id: s.id }))}
               />
             </JobTabs>
          </div>

        </div>
      </main>
    </div>
  );
}
