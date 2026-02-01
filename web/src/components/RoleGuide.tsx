"use client";

import { useEffect, useMemo, useState } from "react";
import { bff } from "@/lib/bffClient";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type EvidenceDraft = { source_url: string; quote?: string; claim?: string };

function short(addr: string) {
  const a = (addr || "").toLowerCase();
  if (!a.startsWith("0x") || a.length < 10) return a;
  return `${a.slice(0, 6)}…${a.slice(-4)}`;
}

export function RoleGuide({
  jobId,
  sponsorAddress,
  jobStatus,
}: {
  jobId: string;
  sponsorAddress: string | null | undefined;
  jobStatus: "open" | "closed";
}) {
  const [me, setMe] = useState<{ authenticated: boolean; address: string | null }>({ authenticated: false, address: null });
  const [stakeText, setStakeText] = useState<string | null>(null);

  const [content, setContent] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [evidence, setEvidence] = useState<EvidenceDraft[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const isSponsor = useMemo(() => {
    if (!me.address || !sponsorAddress) return false;
    return me.address.toLowerCase() === sponsorAddress.toLowerCase();
  }, [me.address, sponsorAddress]);

  useEffect(() => {
    (async () => {
      try {
        const m = await bff.authMe();
        setMe(m);
        if (m.authenticated && m.address) {
          const st = await api.stakeStatus(m.address).catch(() => null);
          setStakeText(st ? `${st.is_eligible ? "eligible" : "not eligible"} | stake=${st.staked_amount}` : null);
        }
      } catch {
        setMe({ authenticated: false, address: null });
      }
    })();
  }, []);

  function addEvidence() {
    setError(null);
    const url = evidenceUrl.trim();
    if (!url) return;
    setEvidence((arr) => [...arr, { source_url: url }]);
    setEvidenceUrl("");
  }

  async function onSubmit() {
    setError(null);
    setOk(null);
    setIsBusy(true);
    try {
      if (jobStatus !== "open") throw new Error("Topic is closed.");
      if (!me.authenticated) throw new Error("Log in first (Account → Log in).");
      const body = {
        job_id: jobId,
        content: content.trim(),
        evidence: evidence.map((e) => ({ type: "web", source_url: e.source_url, quote: e.quote ?? null, claim: e.claim ?? null })),
      };
      if (!body.content) throw new Error("Write your submission first.");
      const res = await bff.submitWork(body);
      setOk(`Submitted: ${res.submission.id.slice(0, 8)}…`);
      setContent("");
      setEvidence([]);
      window.location.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Card className="border-white/5 bg-[#151515]">
      <CardHeader className="pb-3">
        <CardTitle className="text-slate-200">Participation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-slate-300">
        <div className="text-xs text-slate-500">
          Logged in: {me.authenticated && me.address ? short(me.address) : "no"}
          {stakeText ? ` · ${stakeText}` : ""}
          {isSponsor ? " · sponsor" : ""}
        </div>

        {!me.authenticated ? (
          <div className="text-sm text-slate-400">
            Log in from the header (Account → Log in). Your wallet address is your identity.
          </div>
        ) : null}

        {jobStatus === "open" ? (
          <div className="space-y-3">
            <div className="text-xs text-slate-500 space-y-1">
              <div>- Agent: submit your argument with citations/evidence.</div>
              <div>- Jury: vote in the Jury Votes tab with evidence checks.</div>
              <div>- Sponsor: can manually close under override policy (left panel).</div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">Submission</Label>
              <textarea
                className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-[#38bdf8]/50 transition-colors min-h-[140px]"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="State your thesis, then provide evidence links."
                disabled={isBusy}
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">Evidence URL (optional)</Label>
              <div className="flex gap-2">
                <Input value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} placeholder="https://…" disabled={isBusy} />
                <Button type="button" variant="outline" className="border-white/10 text-slate-300 hover:text-white" onClick={addEvidence} disabled={isBusy}>
                  Add
                </Button>
              </div>
              {evidence.length ? (
                <div className="text-xs text-slate-500 space-y-1">
                  {evidence.map((e, i) => (
                    <div key={i} className="font-mono truncate" title={e.source_url}>
                      - {e.source_url}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            <Button onClick={onSubmit} disabled={isBusy || !me.authenticated} className="w-full">
              {isBusy ? "Submitting..." : "Submit Work"}
            </Button>
          </div>
        ) : (
          <div className="text-sm text-slate-500">This topic is closed. You can still discuss and review submissions.</div>
        )}

        {error ? <div className="text-sm text-red-400">Error: {error}</div> : null}
        {ok ? <div className="text-sm text-emerald-400">{ok}</div> : null}
      </CardContent>
    </Card>
  );
}

