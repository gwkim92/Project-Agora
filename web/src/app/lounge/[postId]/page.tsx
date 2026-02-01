"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { bff } from "@/lib/bffClient";
import { DiscussionThread } from "@/components/DiscussionThread";

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

export default function LoungePostPage() {
  const params = useParams<{ postId: string }>();
  const postId = params?.postId ? String(params.postId) : "";
  const [post, setPost] = useState<Post | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!postId) return;
    let cancelled = false;
    bff
      .getPost(postId)
      .then((p) => {
        if (cancelled) return;
        setError(null);
        setPost(p as unknown as Post);
      })
      .catch((e) => {
        if (cancelled) return;
        setPost(null);
        setError(e instanceof Error ? e.message : "Failed to load post");
      });
    return () => {
      cancelled = true;
    };
  }, [postId]);

  if (!postId) {
    return <div className="w-full max-w-[1100px] mx-auto px-6 text-slate-500">Missing post id.</div>;
  }

  return (
    <div className="w-full max-w-[1100px] mx-auto px-6">
      {error ? <div className="text-sm text-red-400">Error: {error}</div> : null}

      {post ? (
        <div className="rounded-2xl border border-white/5 bg-[#151515] p-6">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Lounge Post</div>
          <h1 className="mt-2 text-2xl md:text-3xl font-serif text-slate-100">{post.title}</h1>
          <div className="mt-2 text-xs text-slate-500">
            {short(post.author_address)} · {new Date(post.created_at).toLocaleString()}
          </div>
          {post.tags?.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {post.tags.map((t) => (
                <span key={t} className="text-[11px] px-2 py-1 rounded-full border border-white/10 text-slate-400 bg-white/5">
                  {t}
                </span>
              ))}
            </div>
          ) : null}
          <div className="mt-5 whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">{post.content}</div>
        </div>
      ) : (
        <div className="text-sm text-slate-500">Loading…</div>
      )}

      <div className="mt-8">
        <DiscussionThread targetType="post" targetId={postId} title="Discussion" />
      </div>
    </div>
  );
}

