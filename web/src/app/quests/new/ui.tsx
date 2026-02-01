"use client";

import { useMemo, useState } from "react";
import { bff } from "@/lib/bffClient";
import { TOPICS } from "@/lib/topics";
import { Button } from "@/components/ui/button";
import { Tag, DollarSign, PenTool, Scale } from "lucide-react";

export function NewQuestForm() {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [bounty, setBounty] = useState("25");
  const [topic, setTopic] = useState<string>(TOPICS[0].id);
  const [tags, setTags] = useState("");
  const [finalVoteHours, setFinalVoteHours] = useState("24");
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
      const job = await bff.createJob({
        title: title.trim(),
        prompt: prompt.trim(),
        bounty_usdc: Number(bounty),
        tags: tagList,
        final_vote_window_seconds: finalVoteHours.trim() ? Number(finalVoteHours.trim()) * 3600 : null,
      });
      window.location.href = `/quests/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create quest");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="bg-[#151515] border border-white/5 rounded-2xl overflow-hidden p-8 md:p-12">
      <div className="mb-10 flex items-center justify-between">
        <div>
           <h2 className="text-xl font-serif text-slate-200 mb-2">Topic Parameters</h2>
           <p className="text-sm text-slate-500 font-light">Define the scope and rewards for your inquiry.</p>
        </div>
        <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
           <PenTool className="w-5 h-5 text-[#38bdf8]" />
        </div>
      </div>
      
      <form onSubmit={onSubmit} className="space-y-10">
        
        {/* ROW 1: Sector & Bounty */}
        <div className="grid gap-8 md:grid-cols-2">
          <div className="space-y-3">
            <label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">
              Target Sector
            </label>
            <select
              className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-[#38bdf8]/50 transition-colors appearance-none"
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
          
          <div className="space-y-3">
            <label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
              Bounty Allocation (USDC)
            </label>
            <div className="relative">
              <DollarSign className="absolute left-4 top-3.5 h-4 w-4 text-[#38bdf8]" />
              <input
                className="w-full bg-[#0c0a09] border border-white/10 rounded-lg pl-10 pr-4 py-3 text-sm text-[#38bdf8] font-medium placeholder-slate-700 focus:outline-none focus:border-[#38bdf8]/50 transition-colors"
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

        {/* ROW 2: Title */}
        <div className="space-y-3">
          <label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">Topic Title</label>
          <input
            className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-3 text-lg text-slate-200 font-serif placeholder-slate-700 focus:outline-none focus:border-[#38bdf8]/50 transition-colors"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Analyze the impact of quantum computing on cryptography..."
            required
          />
        </div>

        {/* ROW 3: Prompt */}
        <div className="space-y-3">
          <label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500">The Thesis (Prompt)</label>
          <textarea
            className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-4 text-sm text-slate-300 font-light placeholder-slate-700 min-h-[200px] focus:outline-none focus:border-[#38bdf8]/50 transition-colors leading-relaxed resize-none"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the task in detail. Include specific requirements, data sources, and expected output format..."
            required
          />
        </div>

        {/* ROW 4: Tags */}
        <div className="space-y-3">
          <label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
            <Tag className="h-3 w-3" /> Metadata Tags (CSV)
          </label>
          <input
            className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-700 focus:outline-none focus:border-[#38bdf8]/50 transition-colors"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="defi, security, analysis..."
          />
          <div className="flex flex-wrap gap-2 pt-1 min-h-[24px]">
            {tagList.map(t => (
              <span key={t} className="px-2 py-0.5 bg-white/5 rounded text-xs text-[#38bdf8]">#{t}</span>
            ))}
          </div>
        </div>

        {/* ROW 5: Final decision window */}
        <div className="space-y-3">
          <label className="text-xs font-serif uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
            <Scale className="h-3 w-3" /> Final Vote Window (hours)
          </label>
          <input
            className="w-full bg-[#0c0a09] border border-white/10 rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-700 focus:outline-none focus:border-[#38bdf8]/50 transition-colors"
            value={finalVoteHours}
            onChange={(e) => setFinalVoteHours(e.target.value)}
            type="number"
            min="1"
            max="720"
            step="1"
            required
          />
          <div className="text-xs text-slate-500 font-light">
            After the window ends, finalization is time-locked and can be triggered by anyone who voted.
          </div>
        </div>

        {error ? (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-sm text-red-400">
            Error: {error}
          </div>
        ) : null}

        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full h-14 rounded-full bg-[#e0f2fe] text-[#0f172a] hover:bg-white text-lg font-medium shadow-[0_0_20px_rgba(224,242,254,0.1)] transition-colors"
        >
          {isSubmitting ? "Creating topic…" : "Sponsor Topic"}
        </Button>
      </form>
    </div>
  );
}
