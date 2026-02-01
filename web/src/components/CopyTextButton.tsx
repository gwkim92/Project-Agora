"use client";

import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";

export function CopyTextButton({
  text,
  label = "Copy",
  copiedLabel = "Copied",
  className,
}: {
  text: string;
  label?: string;
  copiedLabel?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // Fallback: execCommand(copy) for browsers that block clipboard API.
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "true");
        ta.style.position = "fixed";
        ta.style.top = "0";
        ta.style.left = "0";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        ta.setSelectionRange(0, ta.value.length);
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (ok) {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
          return;
        }
      } catch {
        // ignore and fall through
      }
      // Last resort: prompt so user can manually copy.
      window.prompt("Copy this text:", text);
    }
  }, [text]);

  return (
    <Button type="button" variant="outline" size="sm" onClick={onCopy} className={className}>
      {copied ? copiedLabel : label}
    </Button>
  );
}

