import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { serverGetJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest, ctx: { params: Promise<{ postId: string }> }) {
  try {
    assertSameOrigin(req);
    const { postId } = await ctx.params;
    const data = await serverGetJson(`/api/v1/posts/${postId}`);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

