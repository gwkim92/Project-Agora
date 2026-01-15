"use client";

import { useMemo, useState } from "react";

import { api } from "@/lib/api";

export function CloseJobForm({
  jobId,
  submissions,
}: {
  jobId: string;
  submissions: Array<{ id: string }>;
}) {
  const [winner, setWinner] = useState(submissions[0]?.id ?? "");
  const [isClosing, setIsClosing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const options = useMemo(() => submissions.map((s) => s.id), [submissions]);

  async function onClose(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setIsClosing(true);
    try {
      const res = await api.closeJob(jobId, winner);
      setResult(`closed: winner ${res.winner_submission_id}`);
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to close job");
    } finally {
      setIsClosing(false);
    }
  }

  return (
    <section className="rounded-xl border bg-white p-4">
      <h2 className="text-sm font-semibold text-zinc-900">Close Job (Sponsor final choice)</h2>
      <p className="mt-1 text-sm text-zinc-600">MVP에서는 스폰서가 최종 승자를 확정합니다.</p>

      {options.length === 0 ? (
        <div className="mt-3 text-sm text-zinc-500">제출물이 없어서 종료할 수 없습니다.</div>
      ) : (
        <form onSubmit={onClose} className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-zinc-900">Winner submission</label>
            <select
              className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
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
          <button
            type="submit"
            disabled={isClosing}
            className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            {isClosing ? "Closing..." : "Close job"}
          </button>
        </form>
      )}

      {error ? <div className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</div> : null}
      {result ? <div className="mt-3 rounded-lg bg-green-50 p-2 text-sm text-green-800">{result}</div> : null}
    </section>
  );
}

