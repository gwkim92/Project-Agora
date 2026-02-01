import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ commentId: string }> }) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const { commentId } = await ctx.params;
    // FastAPI expects DELETE; serverApi helper currently only supports GET/POST.
    // Use fetch directly here.
    const API_BASE = (
      process.env.AGORA_API_BASE ??
      process.env.NEXT_PUBLIC_AGORA_API_BASE ??
      "https://api.project-agora.im"
    ).replace(/\/$/, "");
    const res = await fetch(`${API_BASE}/api/v1/comments/${commentId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const text = await res.text().catch(() => "");
    if (!res.ok) {
      return NextResponse.json({ detail: `DELETE /api/v1/comments/${commentId} failed: ${res.status} ${text}` }, { status: 400 });
    }
    return NextResponse.json(JSON.parse(text));
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

