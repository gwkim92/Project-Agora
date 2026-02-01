"use client";

import { useEffect, useMemo, useState } from "react";
import { bff } from "@/lib/bffClient";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CHECKS = [
  { id: "has_links", label: "Has citations/links" },
  { id: "has_evidence", label: "Has evidence objects" },
  { id: "has_quote", label: "Includes quoted material" },
  { id: "has_snapshot_hash", label: "Includes snapshot/hash" },
] as const;

function short(addr: string) {
  const a = (addr || "").toLowerCase();
  if (!a.startsWith("0x") || a.length < 10) return a;
  return `${a.slice(0, 6)}…${a.slice(-4)}`;
}

export function JuryVotePanel({
  jobId,
  submissions,
  profilesByAddress,
}: {
  jobId: string;
  submissions: Array<{ id: string; agent_address: string; evidence_count?: number }>;
  profilesByAddress?: Record<string, { nickname?: string | null; participant_type?: string }>;
}) {
  const [me, setMe] = useState<{ authenticated: boolean; address: string | null }>({ authenticated: false, address: null });
  const [stakeText, setStakeText] = useState<string | null>(null);
  const [repText, setRepText] = useState<string | null>(null);

  const [choice, setChoice] = useState(submissions[0]?.id ?? "");
  const [note, setNote] = useState("");
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const selected = useMemo(() => submissions.find((s) => s.id === choice) ?? null, [choice, submissions]);

  useEffect(() => {
    (async () => {
      try {
        const m = await bff.authMe();
        setMe(m);
        if (m.authenticated && m.address) {
          const [st, rep] = await Promise.all([
            api.stakeStatus(m.address).catch(() => null),
            api.reputation(m.address).catch(() => null),
          ]);
          setStakeText(st ? `${st.is_eligible ? "eligible" : "not eligible"} | stake=${st.staked_amount}` : null);
          setRepText(rep ? `rep=${rep.score} (lvl ${rep.level})` : null);
        }
      } catch {
        setMe({ authenticated: false, address: null });
      }
    })();
  }, []);

  async function onVote() {
    setError(null);
    setOk(null);
    setIsBusy(true);
    try {
      if (!me.authenticated) throw new Error("Log in first (Account → Log in).");
      if (!choice) throw new Error("Pick a submission");

      const selectedChecks = Object.entries(checks)
        .filter(([, v]) => v)
        .map(([k]) => k);

      const review: Record<string, unknown> = {
        checks: selectedChecks,
        note: note.trim() ? note.trim() : null,
      };

      await bff.castJuryVote(jobId, choice, review);
      setOk(`Voted for #${choice.slice(0, 8)} (review saved)`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Vote failed");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Card className="border-white/5 bg-[#151515]">
      <CardHeader className="pb-3">
        <CardTitle className="text-slate-200">Cast a Jury Vote</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 text-sm text-slate-300">
        <div className="text-xs text-slate-500">
          Logged in: {me.authenticated && me.address ? short(me.address) : "no"}
          {stakeText ? ` · ${stakeText}` : ""}
          {repText ? ` · ${repText}` : ""}
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">Submission</Label>
          <select
            className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-[#38bdf8]/50 transition-colors font-mono"
            value={choice}
            onChange={(e) => setChoice(e.target.value)}
            disabled={isBusy || !submissions.length}
          >
            {submissions.map((s) => (
              <option key={s.id} value={s.id}>
                #{s.id.slice(0, 8)} ·{" "}
                {profilesByAddress?.[String(s.agent_address || "").toLowerCase()]?.nickname
                  ? profilesByAddress?.[String(s.agent_address || "").toLowerCase()]?.nickname
                  : short(s.agent_address)}
              </option>
            ))}
          </select>
          {selected ? (
            <div className="text-xs text-slate-500">
              evidence={selected.evidence_count ?? 0}
            </div>
          ) : null}
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">Evidence checks</Label>
          <div className="grid md:grid-cols-2 gap-2">
            {CHECKS.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={Boolean(checks[c.id])}
                  onChange={(e) => setChecks((m) => ({ ...m, [c.id]: e.target.checked }))}
                  disabled={isBusy}
                />
                {c.label}
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">Note (optional)</Label>
          <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why did you vote this way?" disabled={isBusy} />
        </div>

        <Button onClick={onVote} disabled={isBusy || !submissions.length} className="w-full">
          {isBusy ? "Voting..." : "Vote"}
        </Button>

        {error ? <div className="text-sm text-red-400">Error: {error}</div> : null}
        {ok ? <div className="text-sm text-emerald-400">{ok}</div> : null}
      </CardContent>
    </Card>
  );
}

