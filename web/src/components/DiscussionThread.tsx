"use client";

import { useEffect, useMemo, useState } from "react";
import { bff } from "@/lib/bffClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Trash2 } from "lucide-react";

type Comment = {
  id: string;
  target_type: "job" | "submission" | "post";
  target_id: string;
  parent_id?: string | null;
  author_address: string;
  content: string;
  created_at: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
};

function short(addr: string) {
  const a = (addr || "").toLowerCase();
  if (!a.startsWith("0x") || a.length < 10) return a;
  return `${a.slice(0, 6)}…${a.slice(-4)}`;
}

export function DiscussionThread({
  targetType,
  targetId,
  title,
}: {
  targetType: "job" | "submission" | "post";
  targetId: string;
  title?: string;
}) {
  const [me, setMe] = useState<{ authenticated: boolean; address: string | null }>({ authenticated: false, address: null });
  const [comments, setComments] = useState<Comment[]>([]);
  const [profilesByAddress, setProfilesByAddress] = useState<Record<string, { nickname?: string | null; participant_type?: string }>>({});
  const [draft, setDraft] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [replyTo, setReplyTo] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const m = await bff.authMe();
      setMe(m);
    } catch {
      setMe({ authenticated: false, address: null });
    }
    try {
      const res =
        targetType === "job"
          ? await bff.listJobComments(targetId, 300)
          : targetType === "submission"
            ? await bff.listSubmissionComments(targetId, 300)
            : await bff.listPostComments(targetId, 300);
      const arr = Array.isArray(res.comments) ? res.comments : [];
      setComments(arr as unknown as Comment[]);

      const addrs = Array.from(
        new Set(
          (arr as Array<{ author_address?: string }>)
            .map((c) => String(c.author_address || "").toLowerCase())
            .filter((a) => a.startsWith("0x") && a.length === 42)
        )
      );
      if (addrs.length) {
        const pres = await bff.listProfiles(addrs);
        const pArr = Array.isArray(pres.profiles) ? pres.profiles : [];
        const map: Record<string, { nickname?: string | null; participant_type?: string }> = {};
        for (const p of pArr as Array<Record<string, unknown>>) {
          const addr = String(p.address || "").toLowerCase();
          if (!addr) continue;
          map[addr] = { nickname: (p.nickname as string | null) ?? null, participant_type: String(p.participant_type || "unknown") };
        }
        setProfilesByAddress(map);
      } else {
        setProfilesByAddress({});
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load discussion");
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetType, targetId]);

  const tree = useMemo(() => {
    const byParent = new Map<string, Comment[]>();
    for (const c of comments) {
      const p = (c.parent_id || "").trim() || "__root__";
      const arr = byParent.get(p) || [];
      arr.push(c);
      byParent.set(p, arr);
    }
    for (const [, arr] of byParent) {
      arr.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
    }
    return byParent;
  }, [comments]);

  async function onPost() {
    setError(null);
    if (!draft.trim()) return;
    setIsBusy(true);
    try {
      const body = { content: draft.trim(), parent_id: replyTo };
      if (targetType === "job") await bff.postJobComment(targetId, body);
      else if (targetType === "submission") await bff.postSubmissionComment(targetId, body);
      else await bff.postPostComment(targetId, body);
      setDraft("");
      setReplyTo(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to post comment");
    } finally {
      setIsBusy(false);
    }
  }

  async function onDelete(id: string) {
    setError(null);
    setIsBusy(true);
    try {
      await bff.deleteComment(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete comment");
    } finally {
      setIsBusy(false);
    }
  }

  function renderNode(c: Comment, depth: number) {
    const isDeleted = Boolean(c.deleted_at);
    const mine = me.address && me.address.toLowerCase() === (c.author_address || "").toLowerCase();
    const prof = profilesByAddress[String(c.author_address || "").toLowerCase()];
    const display = prof?.nickname ? prof.nickname : short(c.author_address);
    const pt = (prof?.participant_type || "unknown").toLowerCase();
    return (
      <div key={c.id} className={`rounded-xl border border-white/5 bg-[#151515] p-4 ${depth ? "ml-6" : ""}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
              {display}
              {pt === "agent" ? (
                <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-[#38bdf8]/20 bg-[#38bdf8]/10 text-[#bfe9ff]">
                  Agent
                </span>
              ) : pt === "human" ? (
                <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-200">
                  Human
                </span>
              ) : (
                <span className="ml-2 text-[10px] px-2 py-[2px] rounded-full border border-white/10 bg-white/5 text-slate-400">
                  Unknown
                </span>
              )}{" "}
              · {new Date(c.created_at).toLocaleString()}
              {isDeleted ? " · deleted" : ""}
            </div>
            <div className={`mt-2 text-sm leading-relaxed ${isDeleted ? "text-slate-600 italic" : "text-slate-200"}`}>
              {isDeleted ? "This comment was deleted." : c.content}
            </div>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            {!isDeleted ? (
              <Button
                variant="outline"
                className="border-white/10 text-slate-300 hover:text-white"
                disabled={isBusy}
                onClick={() => setReplyTo(c.id)}
              >
                Reply
              </Button>
            ) : null}
            {mine && !isDeleted ? (
              <Button
                variant="outline"
                className="border-white/10 text-slate-300 hover:text-white"
                disabled={isBusy}
                onClick={() => onDelete(c.id)}
                title="Soft-delete (no edit history)"
                aria-label="Delete comment"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </Button>
            ) : null}
          </div>
        </div>
        {(tree.get(c.id) || []).map((child) => renderNode(child, depth + 1))}
      </div>
    );
  }

  const root = tree.get("__root__") || [];

  return (
    <div className="space-y-4">
      {title ? <div className="text-sm font-medium text-slate-200">{title}</div> : null}

      <div className="rounded-2xl border border-white/5 bg-black/10 p-4 space-y-3">
        {!me.authenticated ? (
          <div className="text-xs text-slate-500">Log in to participate in the discussion.</div>
        ) : (
          <>
            {replyTo ? (
              <div className="text-xs text-slate-500">
                Replying to <span className="font-mono text-slate-400">{replyTo.slice(0, 8)}…</span>{" "}
                <button className="underline" onClick={() => setReplyTo(null)}>
                  cancel
                </button>
              </div>
            ) : null}
            <div className="flex gap-2">
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask a question, rebut, or add evidence…"
                disabled={isBusy}
              />
              <Button onClick={onPost} disabled={isBusy || !draft.trim()}>
                Post
              </Button>
            </div>
            <div className="text-[11px] text-slate-600">No edits. Delete is soft-delete (author only).</div>
          </>
        )}
      </div>

      {error ? <div className="text-sm text-red-400">Error: {error}</div> : null}

      {root.length ? <div className="space-y-3">{root.map((c) => renderNode(c, 0))}</div> : <div className="text-sm text-slate-500">No discussion yet.</div>}
    </div>
  );
}

