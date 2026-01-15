"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { TOPICS } from "@/lib/topics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tag, DollarSign, PenTool } from "lucide-react";

export function NewQuestForm() {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [bounty, setBounty] = useState("25");
  const [topic, setTopic] = useState<string>(TOPICS[0].id);
  const [tags, setTags] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const topicObj = useMemo(() => TOPICS.find((t) => t.id === topic) ?? TOPICS[0], [topic]);
  const tagList = useMemo(() => {
    const extra = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const base = topicObj?.tags?.[0] ? [topicObj.tags[0]] : [];
    return Array.from(new Set([...base, ...extra]));
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
    <Card className="border-slate-800/50 bg-slate-950/50 overflow-hidden">
      <CardHeader className="py-4 bg-slate-900/30 border-b border-slate-800/50">
        <CardTitle className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400 flex items-center gap-2">
            <PenTool className="h-3.5 w-3.5" /> Quest Parameters
          </span>
          <Badge variant="outline" className="text-[9px] font-mono uppercase border-indigo-500/30 text-indigo-400">
            Node Input
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-8">
        <form onSubmit={onSubmit} className="space-y-8">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
                Sector Classification
              </label>
              <select
                className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 font-mono uppercase focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              >
                {TOPICS.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
                Bounty (USDC)
              </label>
              <div className="relative">
                <DollarSign className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-emerald-500" />
                <input
                  className="w-full rounded-md border border-slate-800 bg-slate-950 pl-8 pr-3 py-2 text-sm text-emerald-400 font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
                  value={bounty}
                  onChange={(e) => setBounty(e.target.value)}
                  type="number"
                  min="0"
                  step="1"
                  required
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Quest Title</label>
            <input
              className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 font-mono uppercase placeholder:text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="ENTER QUEST SUBJECT..."
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Prompt Specification</label>
            <textarea
              className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-[11px] text-slate-300 font-mono placeholder:text-slate-700 min-h-[160px] focus:outline-none focus:ring-1 focus:ring-indigo-500/50 leading-relaxed"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="SPECIFY AGENT REQUIREMENTS, OUTPUT FORMAT, AND EVALUATION CRITERIA..."
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
              <Tag className="h-3 w-3" /> Metadata Tags (CSV)
            </label>
            <input
              className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 font-mono placeholder:text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="TAG1, TAG2, TAG3..."
            />
            <div className="flex flex-wrap gap-1.5 pt-1">
              {tagList.map(t => (
                <span key={t} className="text-[9px] font-mono text-indigo-400 uppercase">#{t}</span>
              ))}
            </div>
          </div>

          {error ? (
            <div className="rounded-md bg-red-950/20 border border-red-900/30 p-3 text-[10px] font-mono text-red-400 uppercase">
              Error: {error}
            </div>
          ) : null}

          <Button type="submit" disabled={isSubmitting} className="w-full font-mono uppercase tracking-widest">
            {isSubmitting ? "TRANSMITTING..." : "AUTHORIZE & CREATE QUEST"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
