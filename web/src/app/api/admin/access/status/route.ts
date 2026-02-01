import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { hasAdminAccessCookie } from "@/app/api/_lib/adminAccessCookies";

export async function GET(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const ok = await hasAdminAccessCookie();
    return NextResponse.json({ ok });
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

