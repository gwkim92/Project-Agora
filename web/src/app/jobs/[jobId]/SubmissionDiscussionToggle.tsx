"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DiscussionThread } from "@/components/DiscussionThread";

export function SubmissionDiscussionToggle({ submissionId }: { submissionId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="pt-3 border-t border-white/5">
      <Button
        variant="outline"
        className="border-white/10 text-slate-300 hover:text-white"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide discussion" : "Discuss this submission"}
      </Button>
      {open ? (
        <div className="pt-2">
          <DiscussionThread targetType="submission" targetId={submissionId} title="Submission Thread" />
        </div>
      ) : null}
    </div>
  );
}

