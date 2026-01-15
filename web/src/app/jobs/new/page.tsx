import Link from "next/link";

import { NewJobForm } from "./ui";

export const dynamic = "force-dynamic";

export default function NewJobPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Create Job</h1>
          <p className="mt-1 text-sm text-zinc-600">Phase 1.5: 결제(에스크로)는 아직 오프체인입니다.</p>
        </div>
        <Link className="text-sm text-zinc-700 hover:text-zinc-900" href="/">
          ← Back
        </Link>
      </div>

      <NewJobForm />
    </div>
  );
}

