import type { Evidence, Submission } from "@/lib/types";
import { EvidenceCard } from "@/components/EvidenceCard";
import { SubmissionDiscussionToggle } from "./SubmissionDiscussionToggle";

function short(addr: string) {
  const a = (addr || "").toLowerCase();
  if (!a.startsWith("0x") || a.length < 10) return a;
  return `${a.slice(0, 6)}…${a.slice(-4)}`;
}

function extractUrls(text: string) {
  const re = /(https?:\/\/[^\s)]+)/g;
  return Array.from(text.matchAll(re)).map((m) => m[1]);
}

export function SubmissionCard({
  submission,
  align,
  profile,
}: {
  submission: Submission;
  align: "left" | "right";
  profile?: { nickname?: string | null; participant_type?: string } | null;
}) {
  const urls = extractUrls(submission.content || "");
  const evidence = (submission.evidence || []) as Evidence[];
  const isLeft = align === "left";

  const display = profile?.nickname ? profile.nickname : `Agent ${short(submission.agent_address)}`;
  const pt = (profile?.participant_type || "unknown").toLowerCase();

  return (
    <div className="relative">
      <div className="hidden md:block absolute left-1/2 top-6 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-[#0c0a09] border border-white/20" />
      <div className="grid md:grid-cols-2 gap-6 items-start">
        <div className={isLeft ? "md:pr-10" : "md:pr-10 md:col-start-1 md:row-start-1 md:opacity-30"} />
        <div className={isLeft ? "md:col-start-1" : "md:col-start-2"}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-slate-200">
                {display}
                {pt === "agent" ? (
                  <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-[#38bdf8]/20 bg-[#38bdf8]/10 text-[#bfe9ff]">
                    Agent
                  </span>
                ) : pt === "human" ? (
                  <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-200">
                    Human
                  </span>
                ) : (
                  <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-white/10 bg-white/5 text-slate-400">
                    Unknown
                  </span>
                )}
              </span>
              <span className="text-[10px] font-mono text-slate-600">REF {submission.id.slice(0, 8)}</span>
            </div>
            <span className="text-xs text-slate-500 font-light">{new Date(submission.created_at).toLocaleString()}</span>
          </div>

          <div className="p-6 bg-[#151515] border border-white/5 rounded-2xl hover:border-white/10 transition-colors space-y-5">
            <p className="text-slate-300 font-light leading-relaxed whitespace-pre-wrap text-sm">{submission.content}</p>

            {evidence.length ? (
              <div className="space-y-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Evidence</div>
                <div className="space-y-3">
                  {evidence.map((ev, i) => (
                    <EvidenceCard key={i} evidence={ev} />
                  ))}
                </div>
              </div>
            ) : null}

            {urls.length > 0 ? (
              <div className="pt-5 border-t border-white/5">
                <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 mb-3">Citations</div>
                <ul className="space-y-2">
                  {urls.map((u) => (
                    <li key={u} className="text-xs text-slate-400 break-all">
                      <a className="hover:text-[#38bdf8] transition-colors" href={u} target="_blank" rel="noreferrer">
                        {u}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <SubmissionDiscussionToggle submissionId={submission.id} />
          </div>
        </div>
        <div className={!isLeft ? "md:pl-10" : "md:pl-10 md:col-start-2 md:row-start-1 md:opacity-30"} />
      </div>
    </div>
  );
}

