"use client";

import { useMemo, useState } from "react";

import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function NewJobForm() {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [bounty, setBounty] = useState("25");
  const [tags, setTags] = useState("debate,macro");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const tagList = useMemo(
    () =>
      tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    [tags]
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreatedId(null);
    setIsSubmitting(true);
    try {
      const job = await api.createJob({
        title: title.trim(),
        prompt: prompt.trim(),
        bounty_usdc: Number(bounty),
        tags: tagList,
      });
      setCreatedId(job.id);
      window.location.href = `/jobs/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader className="border-b border-slate-800/50 pb-4">
        <CardTitle className="flex items-center justify-between">
          <span>Job Spec</span>
          <Badge variant="secondary">Sponsor UI</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-200">Title</label>
        <input
          className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="예: 삼성전자 주가 분석해줘"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-200">Prompt</label>
        <textarea
          className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 min-h-44 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="요청 내용(근거/포맷 요구사항 포함)"
          required
        />
        <p className="mt-2 text-xs text-slate-500">Tip: Output/Evidence/Criteria를 명시하면 제출 품질이 좋아집니다.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-slate-200">Bounty (USDC)</label>
          <input
            className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
            value={bounty}
            onChange={(e) => setBounty(e.target.value)}
            type="number"
            min="0"
            step="0.01"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-200">Tags (comma-separated)</label>
          <input
            className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="debate,crypto,security"
          />
        </div>
      </div>

      {error ? <div className="rounded-md bg-red-950/40 border border-red-900 p-2 text-sm text-red-200">{error}</div> : null}
      {createdId ? <div className="text-xs text-slate-500 font-mono">Created: {createdId}</div> : null}

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full"
      >
        {isSubmitting ? "Creating..." : "Create"}
      </Button>
        </form>
      </CardContent>
    </Card>
  );
}

