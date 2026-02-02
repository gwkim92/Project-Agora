import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";

// serverApi helper currently supports GET/POST/PUT only; use fetch for DELETE.
import { serverPostJson } from "@/app/api/_lib/serverApi";

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const body = await req.json();
    const data = await serverPostJson("/api/v1/reactions", body, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const body = await req.json().catch(() => ({}));
    const API_BASE = (process.env.AGORA_API_BASE ?? process.env.NEXT_PUBLIC_AGORA_API_BASE ?? "https://api.project-agora.im").replace(/\/$/, "");
    const res = await fetch(`${API_BASE}/api/v1/reactions`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const text = await res.text().catch(() => "");
    if (!res.ok) {
      return NextResponse.json({ detail: `DELETE /api/v1/reactions failed: ${res.status} ${text}` }, { status: 400 });
    }
    return NextResponse.json(JSON.parse(text));
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

