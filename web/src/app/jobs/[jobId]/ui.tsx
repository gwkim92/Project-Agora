"use client";

import { useMemo, useState } from "react";

import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trophy } from "lucide-react";

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
    <Card className="border-indigo-500/20 bg-indigo-950/10">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-indigo-300">
            <Trophy className="h-4 w-4" />
            Close Job (Sponsor Final)
          </span>
          <Badge variant="outline" className="border-indigo-500/30 text-indigo-300 bg-indigo-500/5">
            Action Required
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-slate-300">
        <p className="text-slate-400">
          MVP에서는 배심 투표는 추천(랭킹)이고, <span className="text-slate-100">최종 승자 확정은 스폰서</span>가 합니다.
        </p>

      {options.length === 0 ? (
        <div className="mt-3 text-sm text-slate-500">제출물이 없어서 종료할 수 없습니다.</div>
      ) : (
        <form onSubmit={onClose} className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
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
          <Button type="submit" disabled={isClosing}>
            {isClosing ? "Closing..." : "Close job"}
          </Button>
        </form>
      )}

        {error ? <div className="mt-3 rounded-md bg-red-950/40 border border-red-900 p-2 text-sm text-red-200">{error}</div> : null}
        {result ? <div className="mt-3 rounded-md bg-emerald-950/30 border border-emerald-900 p-2 text-sm text-emerald-200">{result}</div> : null}
      </CardContent>
    </Card>
  );
}

