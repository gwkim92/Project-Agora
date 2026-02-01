import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { serverGetJson, serverPostJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest, ctx: { params: Promise<{ postId: string }> }) {
  try {
    assertSameOrigin(req);
    const { postId } = await ctx.params;
    const url = new URL(req.url);
    const limit = url.searchParams.get("limit");
    const qs = limit ? `?limit=${encodeURIComponent(limit)}` : "";
    const data = await serverGetJson(`/api/v1/posts/${postId}/comments${qs}`);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ postId: string }> }) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const { postId } = await ctx.params;
    const body = await req.json();
    const data = await serverPostJson(`/api/v1/posts/${postId}/comments`, body, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

