"use client";

import { useCallback, useState } from "react";
import { ThumbsUp } from "lucide-react";
import { Button } from "@/components/ui/button";

type TargetType = "job" | "post" | "submission" | "comment";

export function UpvoteButton({
  targetType,
  targetId,
  initialUpvotes = 0,
  className,
}: {
  targetType: TargetType;
  targetId: string;
  initialUpvotes?: number;
  className?: string;
}) {
  const [upvotes, setUpvotes] = useState<number>(Number(initialUpvotes) || 0);
  const [liked, setLiked] = useState<boolean>(false);
  const [busy, setBusy] = useState(false);

  const onToggle = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      const method = liked ? "DELETE" : "POST";
      const res = await fetch("/api/reactions", {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_type: targetType, target_id: targetId, kind: "upvote" }),
      });
      const text = await res.text().catch(() => "");
      if (!res.ok) {
        // 401: not authenticated (needs wallet-signature login)
        throw new Error(text || `Request failed (${res.status})`);
      }
      const data = JSON.parse(text) as { stats?: Record<string, number> };
      const next = Number(data?.stats?.upvotes ?? upvotes);
      setUpvotes(next);
      setLiked((v) => !v);
    } catch {
      // Silent fail; keep UI responsive in beta.
    } finally {
      setBusy(false);
    }
  }, [busy, liked, targetId, targetType, upvotes]);

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={onToggle}
      disabled={busy}
      className={className}
      title={liked ? "Remove upvote" : "Upvote"}
    >
      <ThumbsUp className="h-4 w-4 mr-2 opacity-70" aria-hidden="true" />
      <span className="font-mono text-xs">{upvotes}</span>
    </Button>
  );
}

