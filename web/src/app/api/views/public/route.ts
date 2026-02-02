import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";

// No auth required: public view ping.
const API_BASE = (
  process.env.AGORA_API_BASE ??
  process.env.NEXT_PUBLIC_AGORA_API_BASE ??
  "https://api.project-agora.im"
).replace(/\/$/, "");

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const body = await req.json();
    const res = await fetch(`${API_BASE}/api/v1/views/public`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const text = await res.text().catch(() => "");
    if (!res.ok) {
      return NextResponse.json({ detail: `POST /api/v1/views/public failed: ${res.status} ${text}` }, { status: 400 });
    }
    return NextResponse.json(JSON.parse(text));
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

