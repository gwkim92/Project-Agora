import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { serverPostJson } from "@/app/api/_lib/serverApi";

export async function POST(req: NextRequest, ctx: { params: Promise<{ jobId: string }> }) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const { jobId } = await ctx.params;
    const body = await req.json();
    const data = await serverPostJson(`/api/v1/jobs/${jobId}/boost`, body, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

