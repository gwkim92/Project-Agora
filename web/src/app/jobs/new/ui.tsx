"use client";

import { useMemo, useState } from "react";

import { api } from "@/lib/api";

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
    <form onSubmit={onSubmit} className="rounded-xl border bg-white p-4 space-y-4">
      <div>
        <label className="block text-sm font-medium text-zinc-900">Title</label>
        <input
          className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="예: 삼성전자 주가 분석해줘"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-zinc-900">Prompt</label>
        <textarea
          className="mt-1 w-full rounded-lg border px-3 py-2 text-sm min-h-40"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="요청 내용(근거/포맷 요구사항 포함)"
          required
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-zinc-900">Bounty (USDC)</label>
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
            value={bounty}
            onChange={(e) => setBounty(e.target.value)}
            type="number"
            min="0"
            step="0.01"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-zinc-900">Tags (comma-separated)</label>
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="debate,crypto,security"
          />
        </div>
      </div>

      {error ? <div className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</div> : null}
      {createdId ? <div className="text-sm text-zinc-600">Created: {createdId}</div> : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
      >
        {isSubmitting ? "Creating..." : "Create"}
      </button>
    </form>
  );
}

