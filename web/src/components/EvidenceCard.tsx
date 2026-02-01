import { ExternalLink } from "lucide-react";

type Evidence = {
  type?: string | null;
  source_url?: string | null;
  retrieved_at?: string | null;
  snapshot_uri?: string | null;
  snapshot_hash?: string | null;
  quote?: string | null;
  claim?: string | null;
  confidence?: number | null;
};

export function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const url = evidence.source_url ?? null;
  const hasUrl = Boolean(url && url.startsWith("http"));
  return (
    <div className="rounded-xl bg-black/20 border border-white/5 p-4 space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
            Evidence{evidence.type ? ` · ${String(evidence.type).toUpperCase()}` : ""}
          </div>
          {hasUrl ? (
            <a
              href={url!}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex items-center gap-2 text-xs text-slate-200 hover:text-white underline underline-offset-4 truncate max-w-full rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-400/60"
              title={url!}
            >
              <ExternalLink className="h-3 w-3 opacity-70" aria-hidden="true" />
              <span className="truncate">{url}</span>
            </a>
          ) : (
            <div className="mt-1 text-xs text-slate-400">{url ? String(url) : "No source URL"}</div>
          )}
        </div>
        {typeof evidence.confidence === "number" ? (
          <div className="shrink-0 text-[10px] font-mono text-slate-500">conf {Math.round(evidence.confidence * 100)}%</div>
        ) : null}
      </div>

      {evidence.claim ? <div className="text-sm text-slate-200 leading-relaxed">{evidence.claim}</div> : null}
      {evidence.quote ? <div className="text-xs text-slate-400 italic leading-relaxed">“{evidence.quote}”</div> : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1">
        {evidence.snapshot_uri ? (
          <div className="truncate" title={evidence.snapshot_uri}>
            snapshot: <span className="font-mono text-slate-400">{evidence.snapshot_uri}</span>
          </div>
        ) : null}
        {evidence.snapshot_hash ? (
          <div className="truncate" title={evidence.snapshot_hash}>
            hash: <span className="font-mono text-slate-400">{evidence.snapshot_hash}</span>
          </div>
        ) : null}
        {evidence.retrieved_at ? (
          <div className="truncate" title={evidence.retrieved_at}>
            retrieved: <span className="font-mono text-slate-400">{evidence.retrieved_at}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

