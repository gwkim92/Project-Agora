"use client";

import { useEffect, useState } from "react";

import { bff } from "@/lib/bffClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [m, setM] = useState<{
    users: number;
    jobs_total: number;
    jobs_open: number;
    submissions_total: number;
    comments_total: number;
    votes_total: number;
    final_votes_total: number;
    active_sessions: number;
  } | null>(null);

  const [cursors, setCursors] = useState<Array<{ key: string; last_block: number; updated_at: string }>>([]);
  const [donations, setDonations] = useState<
    Array<{
      id: string;
      donor_address: string;
      asset_address: string;
      amount_raw: number;
      amount_usd: number | null;
      purpose_id: number | null;
      tx_hash: string;
      chain_id: number;
      block_number: number;
      log_index: number;
      created_at: string;
    }>
  >([]);
  const [anchors, setAnchors] = useState<
    Array<{
      id: string;
      job_id: string;
      schema_version: number;
      anchor_root: string;
      anchor_uri: string;
      anchor_tx_hash: string | null;
      created_at: string;
    }>
  >([]);
  const [suggestedKeys, setSuggestedKeys] = useState<string[]>([]);
  const [cursorKey, setCursorKey] = useState("");
  const [cursorBlock, setCursorBlock] = useState("");
  const [busy, setBusy] = useState(false);
  const [syncResult, setSyncResult] = useState<Record<string, unknown> | null>(null);

  const [receiptJobId, setReceiptJobId] = useState<string>("");
  const [receiptTxHash, setReceiptTxHash] = useState<string>("");
  const [receiptChainId, setReceiptChainId] = useState<string>("");
  const [receiptContract, setReceiptContract] = useState<string>("");
  const [receiptBlock, setReceiptBlock] = useState<string>("");
  const [receiptLogIndex, setReceiptLogIndex] = useState<string>("");

  const [anchorJobId, setAnchorJobId] = useState<string>("");
  const [preparedAnchor, setPreparedAnchor] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await bff.adminMetrics();
        if (!cancelled) setM(data);

        const [cs, ds, as] = await Promise.all([
          bff.adminOnchainCursors(200),
          bff.adminDonationEvents(50),
          bff.adminAnchors(50),
        ]);
        if (cancelled) return;
        setCursors(cs.cursors ?? []);
        setDonations(ds.events ?? []);
        setAnchors(as.anchors ?? []);
        bff
          .adminSuggestedCursorKeys()
          .then((r) => !cancelled && setSuggestedKeys(r.keys ?? []))
          .catch(() => !cancelled && setSuggestedKeys([]));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load metrics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function refresh() {
    setError(null);
    setBusy(true);
    try {
      const [data, cs, ds, as] = await Promise.all([
        bff.adminMetrics(),
        bff.adminOnchainCursors(200),
        bff.adminDonationEvents(50),
        bff.adminAnchors(50),
      ]);
      setM(data);
      setCursors(cs.cursors ?? []);
      setDonations(ds.events ?? []);
      setAnchors(as.anchors ?? []);
      bff
        .adminSuggestedCursorKeys()
        .then((r) => setSuggestedKeys(r.keys ?? []))
        .catch(() => setSuggestedKeys([]));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setBusy(false);
    }
  }

  async function runSyncOnce() {
    setError(null);
    setBusy(true);
    try {
      const res = await bff.adminSyncOnce();
      setSyncResult(res);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "sync_once failed");
    } finally {
      setBusy(false);
    }
  }

  async function setCursor() {
    setError(null);
    setBusy(true);
    try {
      const k = cursorKey.trim();
      const b = Number(cursorBlock);
      if (!k) throw new Error("Cursor key is required.");
      if (!Number.isFinite(b) || b < 0) throw new Error("last_block must be a non-negative number.");
      await bff.adminSetOnchainCursor({ key: k, last_block: b });
      await refresh();
      setCursorKey("");
      setCursorBlock("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to set cursor");
    } finally {
      setBusy(false);
    }
  }

  async function submitAnchorReceipt() {
    setError(null);
    setBusy(true);
    try {
      const job_id = receiptJobId.trim();
      const anchor_tx_hash = receiptTxHash.trim();
      const anchor_chain_id = Number(receiptChainId);
      const anchor_contract_address = receiptContract.trim();
      const anchor_block_number = Number(receiptBlock);
      const anchor_log_index = Number(receiptLogIndex);
      if (!job_id) throw new Error("job_id is required.");
      if (!anchor_tx_hash) throw new Error("anchor_tx_hash is required.");
      if (!Number.isFinite(anchor_chain_id) || anchor_chain_id <= 0) throw new Error("anchor_chain_id must be > 0.");
      if (!anchor_contract_address) throw new Error("anchor_contract_address is required.");
      if (!Number.isFinite(anchor_block_number) || anchor_block_number < 0) throw new Error("anchor_block_number must be >= 0.");
      if (!Number.isFinite(anchor_log_index) || anchor_log_index < 0) throw new Error("anchor_log_index must be >= 0.");
      await bff.adminRecordAnchorReceipt({
        job_id,
        anchor_tx_hash,
        anchor_chain_id,
        anchor_contract_address,
        anchor_block_number,
        anchor_log_index,
      });
      await refresh();
      setReceiptJobId("");
      setReceiptTxHash("");
      setReceiptChainId("");
      setReceiptContract("");
      setReceiptBlock("");
      setReceiptLogIndex("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to record anchor receipt");
    } finally {
      setBusy(false);
    }
  }

  async function prepareAnchorTx() {
    setError(null);
    setBusy(true);
    try {
      const jobId = anchorJobId.trim();
      if (!jobId) throw new Error("job_id is required.");
      const res = await bff.adminPrepareAnchorTx(jobId);
      setPreparedAnchor(res as unknown as Record<string, unknown>);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to prepare anchor tx");
    } finally {
      setBusy(false);
    }
  }

  async function broadcastAnchorTx() {
    setError(null);
    setBusy(true);
    try {
      const jobId = anchorJobId.trim();
      if (!jobId) throw new Error("job_id is required.");
      await bff.adminBroadcastAnchorTx(jobId);
      setPreparedAnchor(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to broadcast anchor tx");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="text-sm text-slate-500">Loading…</div>;
  if (error) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
        <div className="font-semibold">Access denied / failed</div>
        <div className="mt-1 text-xs text-slate-500 break-words">{error}</div>
        <div className="mt-2 text-xs text-slate-500">
          This page requires your wallet address to be listed in <code className="font-mono">AGORA_OPERATOR_ADDRESSES</code> (or dev secret enabled).
        </div>
      </div>
    );
  }

  if (!m) return null;

  const items = [
    { label: "Users", value: m.users },
    { label: "Jobs (total)", value: m.jobs_total },
    { label: "Jobs (open)", value: m.jobs_open },
    { label: "Submissions", value: m.submissions_total },
    { label: "Comments", value: m.comments_total },
    { label: "Jury votes", value: m.votes_total },
    { label: "Final votes", value: m.final_votes_total },
    { label: "Active sessions", value: m.active_sessions },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          Operator-only · Data is best-effort (sync worker + confirmations).
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="border-white/10 text-slate-300 hover:text-white"
            onClick={runSyncOnce}
            disabled={busy}
            title="Run onchain sync once immediately"
          >
            {busy ? "Running..." : "Sync once"}
          </Button>
          <Button variant="outline" className="border-white/10 text-slate-300 hover:text-white" onClick={refresh} disabled={busy}>
            {busy ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </div>

      {syncResult ? (
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-200 font-sans">Last sync_once result</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs text-slate-300 whitespace-pre-wrap break-words">
              {JSON.stringify(syncResult, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {items.map((it) => (
          <Card key={it.label} className="border-white/10 bg-white/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs text-slate-400 font-sans">{it.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-mono text-slate-100">{it.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-white/10 bg-white/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-slate-200 font-sans">Anchoring (AgoraAnchorRegistry)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-300">
          <div className="text-xs text-slate-500">
            Prepare calldata for Safe (recommended) or broadcast via server EOA (demo). Requires server env:{" "}
            <code className="font-mono">AGORA_ANCHORING_ENABLED</code>,{" "}
            <code className="font-mono">AGORA_ANCHOR_REGISTRY_CONTRACT_ADDRESS</code>.
          </div>

          <div className="grid md:grid-cols-3 gap-3 items-end">
            <div className="space-y-2 md:col-span-2">
              <Label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">job_id</Label>
              <Input value={anchorJobId} onChange={(e) => setAnchorJobId(e.target.value)} placeholder="job uuid" disabled={busy} />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="border-white/10 text-slate-300 hover:text-white" onClick={prepareAnchorTx} disabled={busy}>
                Prepare
              </Button>
              <Button className="bg-[#38bdf8] text-black hover:bg-[#7dd3fc]" onClick={broadcastAnchorTx} disabled={busy}>
                Broadcast
              </Button>
            </div>
          </div>

          {preparedAnchor ? (
            <div className="rounded-lg border border-white/10 bg-[#0c0a09] p-3">
              <div className="text-xs text-slate-500 mb-2">Prepared payload (paste into Safe: to + data, value=0)</div>
              <pre className="text-xs text-slate-300 whitespace-pre-wrap break-words">{JSON.stringify(preparedAnchor, null, 2)}</pre>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-white/10 bg-white/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-slate-200 font-sans">Onchain cursors</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="grid gap-2">
              <Label htmlFor="cursorKey" className="text-xs text-slate-500">
                Cursor key
              </Label>
              <Input
                id="cursorKey"
                value={cursorKey}
                onChange={(e) => setCursorKey(e.target.value)}
                placeholder="stake_vault:8453:0x..."
                disabled={busy}
                list="cursorKeySuggestions"
              />
              <datalist id="cursorKeySuggestions">
                {[...new Set([...suggestedKeys, ...cursors.map((c) => c.key)])].map((k) => (
                  <option key={k} value={k} />
                ))}
              </datalist>
              {suggestedKeys.length ? (
                <div className="text-[11px] text-slate-500">
                  Suggestions:{" "}
                  {suggestedKeys.map((k) => (
                    <button
                      key={k}
                      type="button"
                      className="underline text-slate-400 hover:text-slate-200 mr-2"
                      onClick={() => setCursorKey(k)}
                      disabled={busy}
                    >
                      {k}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="cursorBlock" className="text-xs text-slate-500">
                last_block (next_from_block)
              </Label>
              <Input id="cursorBlock" value={cursorBlock} onChange={(e) => setCursorBlock(e.target.value)} placeholder="123456" disabled={busy} />
            </div>
            <div className="flex items-end">
              <Button onClick={setCursor} disabled={busy} className="w-full">
                Set cursor
              </Button>
            </div>
          </div>

          <div className="text-xs text-slate-500">
            Warning: setting a cursor backwards will cause re-indexing. This is intentional for backfills/runbooks.
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-500">
                  <th className="text-left font-medium py-2 pr-3">key</th>
                  <th className="text-left font-medium py-2 pr-3">last_block</th>
                  <th className="text-left font-medium py-2 pr-3">updated_at</th>
                </tr>
              </thead>
              <tbody>
                {cursors.map((c) => (
                  <tr key={c.key} className="border-t border-white/5 text-slate-300">
                    <td className="py-2 pr-3 font-mono">{c.key}</td>
                    <td className="py-2 pr-3 font-mono">{c.last_block}</td>
                    <td className="py-2 pr-3 font-mono text-slate-500">{c.updated_at}</td>
                  </tr>
                ))}
                {!cursors.length ? (
                  <tr className="border-t border-white/5">
                    <td className="py-3 text-slate-500" colSpan={3}>
                      No cursors yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-200 font-sans">Recent donations</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-500">
                  <th className="text-left font-medium py-2 pr-3">donor</th>
                  <th className="text-left font-medium py-2 pr-3">asset</th>
                  <th className="text-left font-medium py-2 pr-3">usd</th>
                  <th className="text-left font-medium py-2 pr-3">block</th>
                </tr>
              </thead>
              <tbody>
                {donations.map((d) => (
                  <tr key={d.id} className="border-t border-white/5 text-slate-300">
                    <td className="py-2 pr-3 font-mono">{d.donor_address}</td>
                    <td className="py-2 pr-3 font-mono">{d.asset_address}</td>
                    <td className="py-2 pr-3 font-mono">{d.amount_usd == null ? "-" : d.amount_usd.toFixed(2)}</td>
                    <td className="py-2 pr-3 font-mono text-slate-500">
                      {d.block_number}:{d.log_index}
                    </td>
                  </tr>
                ))}
                {!donations.length ? (
                  <tr className="border-t border-white/5">
                    <td className="py-3 text-slate-500" colSpan={4}>
                      No donation events yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-white/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-200 font-sans">Recent anchors</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-500">
                  <th className="text-left font-medium py-2 pr-3">job</th>
                  <th className="text-left font-medium py-2 pr-3">uri</th>
                  <th className="text-left font-medium py-2 pr-3">posted</th>
                </tr>
              </thead>
              <tbody>
                {anchors.map((a) => (
                  <tr key={a.id} className="border-t border-white/5 text-slate-300">
                    <td className="py-2 pr-3 font-mono">{a.job_id}</td>
                    <td className="py-2 pr-3">
                      <a className="text-sky-300 hover:text-sky-200 font-mono" href={a.anchor_uri} target="_blank" rel="noreferrer">
                        snapshot
                      </a>
                    </td>
                    <td className="py-2 pr-3 font-mono">{a.anchor_tx_hash ? "yes" : "no"}</td>
                  </tr>
                ))}
                {!anchors.length ? (
                  <tr className="border-t border-white/5">
                    <td className="py-3 text-slate-500" colSpan={3}>
                      No anchors yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      <Card className="border-white/10 bg-white/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-slate-200 font-sans">Record anchor receipt</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-xs text-slate-500">
            After the operator Safe posts <span className="font-mono">postAnchor(...)</span> onchain, record the receipt here to link the job’s offchain snapshot to the onchain tx.
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="grid gap-2">
              <Label className="text-xs text-slate-500">job_id</Label>
              <Input value={receiptJobId} onChange={(e) => setReceiptJobId(e.target.value)} placeholder="job uuid" disabled={busy} />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <Label className="text-xs text-slate-500">anchor_tx_hash</Label>
              <Input value={receiptTxHash} onChange={(e) => setReceiptTxHash(e.target.value)} placeholder="0x…66" disabled={busy} />
            </div>
            <div className="grid gap-2">
              <Label className="text-xs text-slate-500">anchor_chain_id</Label>
              <Input value={receiptChainId} onChange={(e) => setReceiptChainId(e.target.value)} placeholder="8453" disabled={busy} />
            </div>
            <div className="grid gap-2 md:col-span-2">
              <Label className="text-xs text-slate-500">anchor_contract_address</Label>
              <Input value={receiptContract} onChange={(e) => setReceiptContract(e.target.value)} placeholder="0x…42" disabled={busy} />
            </div>
            <div className="grid gap-2">
              <Label className="text-xs text-slate-500">anchor_block_number</Label>
              <Input value={receiptBlock} onChange={(e) => setReceiptBlock(e.target.value)} placeholder="123456" disabled={busy} />
            </div>
            <div className="grid gap-2">
              <Label className="text-xs text-slate-500">anchor_log_index</Label>
              <Input value={receiptLogIndex} onChange={(e) => setReceiptLogIndex(e.target.value)} placeholder="0" disabled={busy} />
            </div>
            <div className="flex items-end">
              <Button onClick={submitAnchorReceipt} disabled={busy} className="w-full">
                Record receipt
              </Button>
            </div>
          </div>
          <div className="text-xs text-slate-500">
            Tip: you can copy <span className="font-mono">job_id</span> from the “Recent anchors” table above.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

