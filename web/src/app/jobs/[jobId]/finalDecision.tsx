"use client";

import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { connectWallet, loadWalletAuth, personalSign, saveWalletAuth, clearWalletAuth } from "@/lib/walletAuth";
import { bff } from "@/lib/bffClient";

function fmt(dt: string | null | undefined) {
  if (!dt) return null;
  const d = new Date(dt);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString();
}

function secondsLeft(endsAt: string | null | undefined) {
  if (!endsAt) return null;
  const end = new Date(endsAt).getTime();
  if (Number.isNaN(end)) return null;
  return Math.floor((end - Date.now()) / 1000);
}

function fmtHMS(totalSeconds: number) {
  const s = Math.max(0, totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(sec)}`;
}

function addSecondsIso(createdAtIso: string, seconds: number): string | null {
  const base = new Date(createdAtIso);
  if (Number.isNaN(base.getTime())) return null;
  const end = new Date(base.getTime() + seconds * 1000);
  return end.toISOString();
}

export function FinalDecisionPanel({
  jobId,
  jobCreatedAt,
  finalVoteStartsAt,
  finalVoteEndsAt,
  submissions,
}: {
  jobId: string;
  jobCreatedAt: string;
  finalVoteStartsAt?: string | null;
  finalVoteEndsAt?: string | null;
  submissions: Array<{ id: string }>;
}) {
  const [address, setAddress] = useState<string | null>(null);
  const [isAuthing, setIsAuthing] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSignedIn, setIsSignedIn] = useState(false);

  const [stakeText, setStakeText] = useState<string | null>(null);
  const [tallyText, setTallyText] = useState<string | null>(null);
  const [defaultWindowSeconds, setDefaultWindowSeconds] = useState<number>(86400);
  const [agrText, setAgrText] = useState<string | null>(null);

  const [choice, setChoice] = useState(submissions[0]?.id ?? "");
  const [isVoting, setIsVoting] = useState(false);
  const [voteError, setVoteError] = useState<string | null>(null);

  const [isFinalizing, setIsFinalizing] = useState(false);
  const [finalizeError, setFinalizeError] = useState<string | null>(null);

  const [boostAmount, setBoostAmount] = useState("10");
  const [boostHours, setBoostHours] = useState("24");
  const [isBoosting, setIsBoosting] = useState(false);
  const [boostError, setBoostError] = useState<string | null>(null);

  const effectiveStartsAt =
    finalVoteStartsAt ??
    addSecondsIso(jobCreatedAt, 0) ??
    null;
  const effectiveEndsAt =
    finalVoteEndsAt ??
    addSecondsIso(jobCreatedAt, defaultWindowSeconds) ??
    null;
  const [nowTick, setNowTick] = useState(0);
  const left = secondsLeft(effectiveEndsAt);
  const votingOpen = left == null ? true : left > 0;
  void nowTick; // referenced via setInterval to trigger re-render for countdown

  const windowLabel = useMemo(() => {
    const s = fmt(effectiveStartsAt);
    const e = fmt(effectiveEndsAt);
    if (s && e) return `${s} → ${e}`;
    return `Default window from creation (${fmt(jobCreatedAt) ?? jobCreatedAt})`;
  }, [finalVoteStartsAt, finalVoteEndsAt, jobCreatedAt]);

  async function refreshTally() {
    try {
      const summ = await api.finalVoteSummary(jobId);
      const lines = (summ.tallies ?? []).map((t) => `${t.submission_id.slice(0, 8)}…  votes=${t.votes}`);
      setTallyText(lines.length ? lines.join("\n") : "No final votes yet.");
    } catch (e) {
      setTallyText(e instanceof Error ? e.message : "Failed to load final vote summary");
    }
  }

  async function refreshStake(addr: string) {
    try {
      const st = await api.stakeStatus(addr);
      setStakeText(`${st.is_eligible ? "eligible" : "not eligible"} | stake=${st.staked_amount}`);
    } catch (e) {
      setStakeText(e instanceof Error ? e.message : "Failed to load stake status");
    }
  }

  async function refreshAgr(addr: string) {
    try {
      const st = await api.agrStatus(addr);
      setAgrText(`AGR balance=${st.balance} (earned=${st.earned}, spent=${st.spent})`);
    } catch (e) {
      setAgrText(e instanceof Error ? e.message : "Failed to load AGR status");
    }
  }

  useEffect(() => {
    const s = loadWalletAuth();
    setAddress(s.address);
    void Promise.all([
      bff
        .authMe()
        .then((me) => setIsSignedIn(Boolean(me.authenticated)))
        .catch(() => setIsSignedIn(false)),
      refreshTally(),
    ]);
  }, [jobId]);

  useEffect(() => {
    api
      .constitution()
      .then((c) => {
        const voting = (c?.voting ?? {}) as Record<string, unknown>;
        const raw = voting["final_vote_window_seconds_default"];
        const n = Number(raw);
        if (Number.isFinite(n) && n > 0) setDefaultWindowSeconds(n);
      })
      .catch(() => {
        // keep fallback
      });
  }, []);

  // countdown tick (no need for perfect precision)
  useEffect(() => {
    const t = window.setInterval(() => setNowTick((x) => x + 1), 1000);
    return () => window.clearInterval(t);
  }, []);

  // auto-refresh tally periodically (so UI updates without manual reload)
  useEffect(() => {
    const t = window.setInterval(() => refreshTally(), 5000);
    return () => window.clearInterval(t);
  }, [jobId]);

  useEffect(() => {
    if (!address) return;
    void Promise.all([refreshStake(address), refreshAgr(address)]);
  }, [address]);

  async function onConnect() {
    // Keep backward compat: connect + then prompt sign-in explicitly (older UX).
    // (HeaderAuth now merges these two into one step.)
    setAuthError(null);
    const addr = await connectWallet();
    setAddress(addr);
    saveWalletAuth({ address: addr });
  }

  async function onLogin() {
    setAuthError(null);
    setIsAuthing(true);
    try {
      const addr = address ?? (await connectWallet());
      setAddress(addr);
      saveWalletAuth({ address: addr });
      const ch = await bff.authChallenge(addr);
      const sig = await personalSign(addr, ch.message_to_sign);
      await bff.authVerify(addr, sig);
      setIsSignedIn(true);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Auth failed");
    } finally {
      setIsAuthing(false);
    }
  }

  async function onSignIn() {
    if (!address) throw new Error("Connect wallet first");
    setAuthError(null);
    setIsAuthing(true);
    try {
      const ch = await bff.authChallenge(address);
      const sig = await personalSign(address, ch.message_to_sign);
      await bff.authVerify(address, sig);
      setIsSignedIn(true);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Auth failed");
    } finally {
      setIsAuthing(false);
    }
  }

  async function onSignOut() {
    try {
      await bff.authLogout();
    } finally {
      clearWalletAuth();
      setIsSignedIn(false);
    }
  }

  async function onCastVote() {
    if (!isSignedIn) {
      setVoteError("Sign in first");
      return;
    }
    setVoteError(null);
    setIsVoting(true);
    try {
      await bff.castFinalVote(jobId, choice);
      await refreshTally();
    } catch (e) {
      setVoteError(e instanceof Error ? e.message : "Failed to cast final vote");
    } finally {
      setIsVoting(false);
    }
  }

  async function onFinalize() {
    if (!isSignedIn) {
      setFinalizeError("Sign in first");
      return;
    }
    setFinalizeError(null);
    setIsFinalizing(true);
    try {
      await bff.finalizeJob(jobId);
      window.location.reload();
    } catch (e) {
      setFinalizeError(e instanceof Error ? e.message : "Finalize failed");
    } finally {
      setIsFinalizing(false);
    }
  }

  async function onBoost() {
    if (!isSignedIn) {
      setBoostError("Sign in first");
      return;
    }
    setBoostError(null);
    setIsBoosting(true);
    try {
      const amt = Number(boostAmount.trim());
      const hrs = Number(boostHours.trim());
      await bff.boostJob(jobId, { amount_agr: amt, duration_hours: hrs });
      await Promise.all([refreshTally(), address ? refreshAgr(address) : Promise.resolve()]);
      window.location.reload();
    } catch (e) {
      setBoostError(e instanceof Error ? e.message : "Boost failed");
    } finally {
      setIsBoosting(false);
    }
  }

  return (
    <Card className="border-emerald-500/20 bg-emerald-950/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-emerald-300">
            Final Decision
          </span>
          <Badge variant="outline" className="border-emerald-500/30 text-emerald-300 bg-emerald-500/5">
            {votingOpen ? "VOTING OPEN" : "VOTING ENDED"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate-300 space-y-4">
        <div className="text-xs text-slate-400">
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 mb-1">Window</div>
          <div>{windowLabel}</div>
          {left != null ? <div className="mt-1">Time left: {fmtHMS(left)}</div> : null}
        </div>

        <div className="rounded-xl bg-black/20 border border-white/5 p-3 space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Wallet</div>
          <div className="text-xs text-slate-300 space-y-2">
            <div className="flex flex-wrap gap-2 items-center">
              <Button type="button" onClick={onLogin} disabled={isAuthing}>
                {isAuthing ? "Logging in..." : isSignedIn ? "Logged in" : "Login with wallet"}
              </Button>
              {isSignedIn ? (
                <Button type="button" variant="outline" onClick={onSignOut}>
                  Sign out
                </Button>
              ) : null}
            </div>
            <div className="font-mono text-[11px] text-slate-400 break-all">{address ? address : "not connected"}</div>
            <div className="text-[11px] text-slate-500">{stakeText ?? ""}</div>
            <div className="text-[11px] text-slate-500">{agrText ?? ""}</div>
            {authError ? <div className="text-xs text-red-200">{authError}</div> : null}
          </div>
        </div>

        <div className="rounded-xl bg-black/20 border border-white/5 p-3 space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Tally</div>
          <pre className="text-[11px] text-slate-300 whitespace-pre-wrap font-mono">{tallyText ?? "Loading..."}</pre>
          <div className="text-[10px] text-slate-600">auto-refresh: 5s</div>
        </div>

        {submissions.length ? (
          <div className="rounded-xl bg-black/20 border border-white/5 p-3 space-y-3">
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Cast final vote</div>
            <select
              className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 font-mono"
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
            >
              {submissions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id}
                </option>
              ))}
            </select>
            <Button type="button" onClick={onCastVote} disabled={isVoting || !votingOpen}>
              {isVoting ? "Voting..." : votingOpen ? "Vote" : "Voting ended"}
            </Button>
            {voteError ? <div className="text-xs text-red-200">{voteError}</div> : null}
          </div>
        ) : (
          <div className="text-xs text-slate-500 italic">No submissions yet.</div>
        )}

        <div className="pt-2 border-t border-white/5">
          <Button type="button" onClick={onFinalize} disabled={isFinalizing || votingOpen}>
            {isFinalizing ? "Finalizing..." : "Finalize (close by votes)"}
          </Button>
          {finalizeError ? <div className="mt-2 text-xs text-red-200">{finalizeError}</div> : null}
        </div>

        <div className="pt-4 border-t border-white/5 space-y-3">
          <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Premium / Curation</div>
          <div className="text-xs text-slate-400">
            Spend AGR credits to feature this topic in Explore (offchain credits; no gas sponsorship).
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400">amount_agr</label>
              <input
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                value={boostAmount}
                onChange={(e) => setBoostAmount(e.target.value)}
                type="number"
                min="1"
                step="1"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400">duration_hours</label>
              <input
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                value={boostHours}
                onChange={(e) => setBoostHours(e.target.value)}
                type="number"
                min="1"
                max="720"
                step="1"
              />
            </div>
          </div>
          <Button type="button" onClick={onBoost} disabled={isBoosting}>
            {isBoosting ? "Boosting..." : "Boost Topic"}
          </Button>
          {boostError ? <div className="text-xs text-red-200">{boostError}</div> : null}
        </div>
      </CardContent>
    </Card>
  );
}

