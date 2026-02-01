import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { hasAdminAccessCookie } from "@/app/api/_lib/adminAccessCookies";
import { serverGetJson, serverPostJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const ok = await hasAdminAccessCookie();
    if (!ok) return NextResponse.json({ detail: "Admin signature required" }, { status: 401 });
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const data = await serverGetJson("/api/v1/admin/onchain/cursors", { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const ok = await hasAdminAccessCookie();
    if (!ok) return NextResponse.json({ detail: "Admin signature required" }, { status: 401 });
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const body = await req.json();
    const data = await serverPostJson("/api/v1/admin/onchain/cursors", body, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

