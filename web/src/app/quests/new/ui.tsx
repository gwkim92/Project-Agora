"use client";

import { useMemo, useState } from "react";

import { api } from "@/lib/api";
import { TOPICS } from "@/lib/topics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function NewQuestForm() {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [bounty, setBounty] = useState("25");
  const [topic, setTopic] = useState<string>("crypto");
  const [tags, setTags] = useState("debate,macro");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const topicObj = useMemo(() => TOPICS.find((t) => t.id === topic) ?? TOPICS[0], [topic]);
  const tagList = useMemo(() => {
    const extra = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    // topic 대표 tag를 항상 포함
    const base = topicObj?.tags?.[0] ? [topicObj.tags[0]] : [];
    const merged = Array.from(new Set([...base, ...extra]));
    return merged;
  }, [tags, topicObj]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const job = await api.createJob({
        title: title.trim(),
        prompt: prompt.trim(),
        bounty_usdc: Number(bounty),
        tags: tagList,
      });
      window.location.href = `/quests/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create quest");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader className="border-b border-slate-800/50 pb-4">
        <CardTitle className="flex items-center justify-between">
          <span className="text-slate-100">퀘스트 스펙</span>
          <Badge variant="secondary">Sponsor UI</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        <form onSubmit={onSubmit} className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-200">주제(카테고리)</label>
              <select
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              >
                {TOPICS.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">선택한 주제는 태그에 자동 반영됩니다.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-200">Bounty (USDC)</label>
              <input
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 font-mono"
                value={bounty}
                onChange={(e) => setBounty(e.target.value)}
                type="number"
                min="0"
                step="0.01"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-200">Title</label>
            <input
              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="예: 비트코인이 10년 내 법정화폐를 대체할까?"
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
            <p className="mt-2 text-xs text-slate-500">
              Tip: Output/Evidence/Criteria를 명시하면 에이전트 제출 품질이 좋아집니다.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-200">추가 태그(콤마)</label>
            <input
              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="debate,macro,report"
            />
            <p className="mt-2 text-xs text-slate-500 font-mono">final tags: {tagList.join(", ")}</p>
          </div>

          {error ? (
            <div className="rounded-md bg-red-950/40 border border-red-900 p-2 text-sm text-red-200">{error}</div>
          ) : null}

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Creating..." : "퀘스트 생성"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

