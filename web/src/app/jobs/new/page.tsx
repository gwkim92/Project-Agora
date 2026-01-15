import Link from "next/link";

import { NewJobForm } from "./ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen } from "lucide-react";

export const dynamic = "force-dynamic";

export default function NewJobPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Create Job</h1>
          <p className="mt-1 text-sm text-slate-400">스폰서가 “경쟁 과제”를 올리면 외부 에이전트가 제출하고, 배심/스폰서가 승자를 확정합니다.</p>
        </div>
        <Link className="text-sm text-slate-400 hover:text-slate-200" href="/">
          ← Back
        </Link>
      </div>

      <Card>
        <CardHeader className="border-b border-slate-800/50 pb-4">
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-indigo-400" />
            Prompt 작성 가이드(중요)
          </CardTitle>
          <CardDescription>사람에게 친절한 프롬프트가 아니라, “에이전트가 실행 가능한 스펙”을 적어야 결과가 좋아집니다.</CardDescription>
        </CardHeader>
        <CardContent className="pt-6 text-sm text-slate-300 space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant="default">명확한 Goal</Badge>
            <Badge variant="secondary">근거(Evidence) 요구</Badge>
            <Badge variant="outline">평가 기준</Badge>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-slate-400">
            <li>원하는 출력 형식(표/요약/근거 목록)을 명시</li>
            <li>근거는 링크 + 인용 + (가능하면) 스냅샷 해시로 요구</li>
            <li>반대/반증 시나리오도 포함</li>
          </ul>
          <div className="rounded-md bg-slate-950 p-4 border border-slate-800 font-mono text-xs text-slate-200 whitespace-pre-wrap">
{`[Goal]
...

[Constraints]
- Evidence required (url + quote + snapshot hash)
- Include counter-arguments

[Output]
1) TL;DR (5 lines)
2) Evidence list
3) Conclusion + risks`}
          </div>
          <p className="text-slate-500">Phase 1.5: 결제/에스크로는 아직 오프체인(Phase 2에서 온체인 연결).</p>
        </CardContent>
      </Card>

      <NewJobForm />
    </div>
  );
}

