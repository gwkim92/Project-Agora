"use client";

import { useEffect, useMemo, useState } from "react";

import { bff } from "@/lib/bffClient";
import { txUrl } from "@/lib/explorers";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trophy } from "lucide-react";

export function CloseJobForm({
  jobId,
  submissions,
  sponsorAddress,
}: {
  jobId: string;
  submissions: Array<{ id: string }>;
  sponsorAddress: string | null | undefined;
}) {
  const [winner, setWinner] = useState(submissions[0]?.id ?? "");
  const [closeTxHash, setCloseTxHash] = useState("");
  const [closeChainId, setCloseChainId] = useState("");
  const [closeContractAddress, setCloseContractAddress] = useState("");
  const [closeBlockNumber, setCloseBlockNumber] = useState("");
  const [closeLogIndex, setCloseLogIndex] = useState("");
  const [isClosing, setIsClosing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const options = useMemo(() => submissions.map((s) => s.id), [submissions]);
  const [me, setMe] = useState<{ authenticated: boolean; address: string | null }>({ authenticated: false, address: null });

  const isSponsor = useMemo(() => {
    if (!me.address || !sponsorAddress) return false;
    return me.address.toLowerCase() === sponsorAddress.toLowerCase();
  }, [me.address, sponsorAddress]);

  useEffect(() => {
    void (async () => {
      try {
        const m = await bff.authMe();
        setMe(m);
      } catch {
        setMe({ authenticated: false, address: null });
      }
    })();
  }, []);

  async function onClose(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setIsClosing(true);
    try {
      if (!me.authenticated) throw new Error("Log in first (Account → Log in).");
      if (!isSponsor) throw new Error("Only the sponsor can manually close this topic.");

      const res = await bff.closeJob(jobId, {
        winner_submission_id: winner,
        close_tx_hash: closeTxHash.trim() ? closeTxHash.trim() : null,
        close_chain_id: closeChainId.trim() ? Number(closeChainId.trim()) : null,
        close_contract_address: closeContractAddress.trim() ? closeContractAddress.trim() : null,
        close_block_number: closeBlockNumber.trim() ? Number(closeBlockNumber.trim()) : null,
        close_log_index: closeLogIndex.trim() ? Number(closeLogIndex.trim()) : null,
      });
      setResult(`closed: winner ${res.winner_submission_id}`);
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to close job");
    } finally {
      setIsClosing(false);
    }
  }

  return (
    <Card className="border-indigo-500/20 bg-indigo-950/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-indigo-300">
            <Trophy className="h-4 w-4" aria-hidden="true" />
            Manual Close (Override)
          </span>
          <Badge variant="outline" className="border-indigo-500/30 text-indigo-300 bg-indigo-500/5">
            Override
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate-300">
        <p className="text-slate-400">
          Final winner is normally decided by Final Decision votes. Use this only under an override policy.
        </p>
        <div className="mt-2 text-xs text-slate-500">
          Status: {me.authenticated && me.address ? `logged in as ${me.address.slice(0, 6)}…` : "not logged in"} ·{" "}
          {isSponsor ? "You are the sponsor." : "Sponsor-only action."}
        </div>

      {options.length === 0 ? (
        <div className="mt-3 text-sm text-slate-500">No submissions yet—this job cannot be closed.</div>
      ) : (
        <form onSubmit={onClose} className="mt-3 flex flex-col gap-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1">
            <label className="block text-sm font-medium text-slate-200">Winner submission</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 font-mono"
              value={winner}
              onChange={(e) => setWinner(e.target.value)}
            >
              {options.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
            </div>
            <Button type="submit" disabled={isClosing || !me.authenticated || !isSponsor}>
              {isClosing ? "Closing..." : "Close job"}
            </Button>
          </div>

          <div className="rounded-xl bg-black/20 border border-white/5 p-3 space-y-3">
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Onchain receipt (optional)</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400">close_tx_hash</label>
                <input
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                  placeholder="0x… (66 chars)"
                  value={closeTxHash}
                  onChange={(e) => setCloseTxHash(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400">close_chain_id</label>
                <input
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                  placeholder="e.g. 1, 8453, 42161"
                  value={closeChainId}
                  onChange={(e) => setCloseChainId(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400">close_contract_address</label>
                <input
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                  placeholder="0x… (42 chars)"
                  value={closeContractAddress}
                  onChange={(e) => setCloseContractAddress(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400">close_block_number</label>
                  <input
                    className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                    placeholder="e.g. 123456"
                    value={closeBlockNumber}
                    onChange={(e) => setCloseBlockNumber(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400">close_log_index</label>
                  <input
                    className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-100 font-mono"
                    placeholder="e.g. 0"
                    value={closeLogIndex}
                    onChange={(e) => setCloseLogIndex(e.target.value)}
                  />
                </div>
              </div>
            </div>
            {txUrl(closeChainId.trim() ? Number(closeChainId.trim()) : null, closeTxHash.trim() ? closeTxHash.trim() : null) ? (
              <a
                className="inline-flex text-[11px] text-slate-400 hover:text-white underline underline-offset-4"
                href={txUrl(
                  closeChainId.trim() ? Number(closeChainId.trim()) : null,
                  closeTxHash.trim() ? closeTxHash.trim() : null
                )!}
                target="_blank"
                rel="noreferrer"
              >
                Explorer preview
              </a>
            ) : null}
          </div>
        </form>
      )}

        {error ? <div className="mt-3 rounded-md bg-red-950/40 border border-red-900 p-2 text-sm text-red-200">{error}</div> : null}
        {result ? <div className="mt-3 rounded-md bg-emerald-950/30 border border-emerald-900 p-2 text-sm text-emerald-200">{result}</div> : null}
      </CardContent>
    </Card>
  );
}

