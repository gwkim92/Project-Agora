import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { serverPostJson } from "@/app/api/_lib/serverApi";

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const body = (await req.json()) as { address?: string };
    const address = String(body?.address ?? "");
    const data = await serverPostJson("/api/v1/agents/auth/challenge", { address });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

