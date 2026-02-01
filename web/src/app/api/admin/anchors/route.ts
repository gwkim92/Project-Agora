import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { hasAdminAccessCookie } from "@/app/api/_lib/adminAccessCookies";
import { serverGetJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const ok = await hasAdminAccessCookie();
    if (!ok) return NextResponse.json({ detail: "Admin signature required" }, { status: 401 });
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const url = new URL(req.url);
    const limit = url.searchParams.get("limit");
    const qs = new URLSearchParams();
    if (limit) qs.set("limit", limit);
    const data = await serverGetJson(`/api/v1/admin/anchors${qs.toString() ? `?${qs.toString()}` : ""}`, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

