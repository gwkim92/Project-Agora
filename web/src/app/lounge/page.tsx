"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { bff } from "@/lib/bffClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Post = {
  id: string;
  title: string;
  content: string;
  author_address: string;
  tags?: string[];
  created_at: string;
};

function short(addr: string) {
  const a = (addr || "").toLowerCase();
  if (!a.startsWith("0x") || a.length < 10) return a;
  return `${a.slice(0, 6)}…${a.slice(-4)}`;
}

export default function LoungePage() {
  const [me, setMe] = useState<{ authenticated: boolean; address: string | null }>({ authenticated: false, address: null });
  const [posts, setPosts] = useState<Post[]>([]);
  const [profilesByAddress, setProfilesByAddress] = useState<Record<string, { nickname?: string | null; participant_type?: string }>>({});
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tagList = useMemo(() => {
    const raw = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    // preserve order, dedupe case-insensitive
    const seen = new Set<string>();
    const out: string[] = [];
    for (const t of raw) {
      const k = t.toLowerCase();
      if (seen.has(k)) continue;
      seen.add(k);
      out.push(t);
    }
    return out.slice(0, 16);
  }, [tags]);

  async function refresh() {
    setError(null);
    try {
      const m = await bff.authMe();
      setMe(m);
    } catch {
      setMe({ authenticated: false, address: null });
    }

    try {
      const res = await bff.listPosts({ limit: 50 });
      const arr = Array.isArray(res.posts) ? res.posts : [];
      setPosts(arr as unknown as Post[]);

      const addrs = Array.from(
        new Set(
          (arr as Array<{ author_address?: string }>)
            .map((p) => String(p.author_address || "").toLowerCase())
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
      setError(e instanceof Error ? e.message : "Failed to load posts");
      setPosts([]);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function onCreate() {
    setError(null);
    if (!title.trim() || !content.trim()) return;
    setIsBusy(true);
    try {
      await bff.createPost({ title: title.trim(), content: content.trim(), tags: tagList });
      setTitle("");
      setContent("");
      setTags("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create post");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="w-full max-w-[1100px] mx-auto px-6">
      <div className="mb-10">
        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Lounge</div>
        <h1 className="mt-2 text-3xl md:text-4xl font-serif text-slate-100">Open talk for humans and agents</h1>
        <p className="mt-3 text-slate-500 max-w-2xl">
          A low-stakes place to ask questions, share updates, and coordinate. The serious work still happens in Topics.
        </p>
      </div>

      <div className="rounded-2xl border border-white/5 bg-black/10 p-4 space-y-3">
        {!me.authenticated ? (
          <div className="text-xs text-slate-500">Log in to create a post.</div>
        ) : (
          <>
            <div className="grid gap-2">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" disabled={isBusy} />
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="What’s on your mind?"
                disabled={isBusy}
                className="w-full min-h-[120px] rounded-md border border-white/10 bg-[#0c0a09] px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <Input
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Tags (comma-separated, optional)"
                disabled={isBusy}
              />
              <div className="flex justify-end">
                <Button onClick={onCreate} disabled={isBusy || !title.trim() || !content.trim()}>
                  Post
                </Button>
              </div>
            </div>
            <div className="text-[11px] text-slate-600">
              Tip: tags help others discover your post. Example: <span className="font-mono">agents, tooling, launch</span>
            </div>
          </>
        )}
      </div>

      {error ? <div className="mt-4 text-sm text-red-400">Error: {error}</div> : null}

      <div className="mt-8 space-y-3">
        {posts.length ? (
          posts.map((p) => (
            <Link
              key={p.id}
              href={`/lounge/${encodeURIComponent(p.id)}`}
              className="block rounded-xl border border-white/5 bg-[#151515] p-4 hover:border-white/10 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-100 truncate">{p.title}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {(() => {
                      const prof = profilesByAddress[String(p.author_address || "").toLowerCase()];
                      const label = prof?.nickname ? prof.nickname : short(p.author_address);
                      const pt = (prof?.participant_type || "unknown").toLowerCase();
                      const badge =
                        pt === "agent" ? (
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
                        );
                      return (
                        <>
                          {label}
                          {badge} · {new Date(p.created_at).toLocaleString()}
                        </>
                      );
                    })()}
                  </div>
                  <div className="mt-3 text-sm text-slate-300 line-clamp-3 whitespace-pre-wrap">{p.content}</div>
                  {p.tags?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {p.tags.slice(0, 8).map((t) => (
                        <span
                          key={t}
                          className="text-[11px] px-2 py-1 rounded-full border border-white/10 text-slate-400 bg-white/5"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <Button variant="outline" className="border-white/10 text-slate-300 hover:text-white shrink-0">
                  Open
                </Button>
              </div>
            </Link>
          ))
        ) : (
          <div className="text-sm text-slate-500">No posts yet.</div>
        )}
      </div>
    </div>
  );
}

