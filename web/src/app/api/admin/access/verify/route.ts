import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { ADMIN_ACCESS_COOKIE_NAME } from "@/app/api/_lib/adminAccessCookies";
import { serverPostJson } from "@/app/api/_lib/serverApi";

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const body = await req.json();
    const data = await serverPostJson("/api/v1/admin/access/verify", body, { token });
    const ttlSeconds = 600;
    const resp = NextResponse.json(data);
    resp.cookies.set(ADMIN_ACCESS_COOKIE_NAME, "1", {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      maxAge: ttlSeconds,
      path: "/",
    });
    return resp;
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

