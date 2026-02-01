import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { serverGetJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const data = await serverGetJson("/api/v1/admin/onchain/suggested_cursor_keys", { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

