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
      // Fallback: best-effort prompt (some environments block clipboard API)
      window.prompt("Copy this text:", text);
    }
  }, [text]);

  return (
    <Button type="button" variant="outline" size="sm" onClick={onCopy} className={className}>
      {copied ? copiedLabel : label}
    </Button>
  );
}

