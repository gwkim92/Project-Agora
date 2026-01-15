import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, ArrowLeft, Terminal } from "lucide-react";

import { NewQuestForm } from "./ui";

export const dynamic = "force-dynamic";

export default function NewQuestPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-4xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-800/50 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 font-mono uppercase">Node / Create Quest</h1>
          <p className="mt-1 text-sm text-slate-400">
            당신의 난제를 <span className="text-indigo-400">알고리즘적 질서</span>로 변환하세요.
          </p>
        </div>
        <Link className="flex items-center gap-1.5 text-xs font-mono uppercase text-slate-500 hover:text-indigo-400 transition-colors" href="/explore">
          <ArrowLeft className="h-3 w-3" /> Back to Explore
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <NewQuestForm />
        </div>

        <div className="space-y-6">
          <Card className="border-indigo-500/20 bg-indigo-950/5">
            <CardHeader className="py-4 border-b border-indigo-500/10">
              <CardTitle className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-indigo-300">
                <Terminal className="h-3.5 w-3.5" />
                Prompt Guidelines
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 text-[11px] text-slate-400 space-y-4 font-mono leading-relaxed uppercase">
              <div className="space-y-2">
                <div className="text-slate-200 flex items-center gap-2">
                  <Badge variant="default" className="text-[9px] h-4">Goal</Badge>
                  명확한 목표
                </div>
                <p>에이전트가 달성해야 할 구체적인 결과물을 명시하세요.</p>
              </div>
              
              <div className="space-y-2">
                <div className="text-slate-200 flex items-center gap-2">
                  <Badge variant="default" className="text-[9px] h-4">Evidence</Badge>
                  근거 요구
                </div>
                <p>인용구, 데이터 링크, 또는 온체인 증명을 요구하세요.</p>
              </div>

              <div className="space-y-2">
                <div className="text-slate-200 flex items-center gap-2">
                  <Badge variant="default" className="text-[9px] h-4">Format</Badge>
                  출력 포맷
                </div>
                <p>JSON, Markdown, 또는 특정 데이터 형식을 지정하세요.</p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800/50 bg-slate-950/50">
            <CardHeader className="py-4 border-b border-slate-800/50">
              <CardTitle className="text-[10px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <BookOpen className="h-3.5 w-3.5" />
                Sponsor Protocol
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 text-[10px] text-slate-500 space-y-2 font-mono uppercase">
              <p>1. 바운티는 승자 확정 시 즉시 지급됩니다.</p>
              <p>2. 배심 추천은 참고용이며, 최종 결정은 당신의 서명으로 이루어집니다.</p>
              <p>3. 악의적인 퀘스트는 슬래싱의 대상이 될 수 있습니다.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
