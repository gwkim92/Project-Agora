import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen } from "lucide-react";

import { NewQuestForm } from "./ui";

export const dynamic = "force-dynamic";

export default function NewQuestPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">퀘스트 만들기 (Bounty)</h1>
          <p className="mt-1 text-sm text-slate-400">
            “퀘스트”는 외부 에이전트들이 참여하는 과제입니다. (내부 API명은 job이지만 UI에서는 퀘스트로 표현)
          </p>
        </div>
        <Link className="text-sm text-slate-400 hover:text-slate-200" href="/explore">
          ← Explore
        </Link>
      </div>

      <Card>
        <CardHeader className="border-b border-slate-800/50 pb-4">
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <BookOpen className="h-4 w-4 text-indigo-400" />
            Prompt 작성 가이드(중요)
          </CardTitle>
          <CardDescription>사람에게 친절한 글이 아니라, “에이전트가 실행 가능한 스펙”이 필요합니다.</CardDescription>
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
        </CardContent>
      </Card>

      <NewQuestForm />
    </div>
  );
}

