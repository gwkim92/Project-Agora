"use client";

import { useEffect } from "react";

type TargetType = "job" | "post" | "submission";

function getViewerKey(): string {
  try {
    const k = localStorage.getItem("agora_viewer_key");
    if (k && k.length >= 8) return k;
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    const v = Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    const key = `v_${v}`; // allowed chars: [A-Za-z0-9_-]
    localStorage.setItem("agora_viewer_key", key);
    return key;
  } catch {
    // Fallback: unstable key (still dedupes within page load)
    return `v_${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}`.slice(0, 32);
  }
}

export function ViewPing({ targetType, targetId }: { targetType: TargetType; targetId: string }) {
  useEffect(() => {
    if (!targetId) return;
    const viewer_key = getViewerKey();
    fetch("/api/views/public", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_type: targetType, target_id: targetId, viewer_key }),
      // keepalive helps when navigating quickly
      keepalive: true,
    }).catch(() => {});
  }, [targetId, targetType]);

  return null;
}

