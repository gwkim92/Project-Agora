import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { serverGetJson, serverPostJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const url = new URL(req.url);
    const tag = url.searchParams.get("tag");
    const limit = url.searchParams.get("limit");
    const qs = new URLSearchParams();
    if (tag) qs.set("tag", tag);
    if (limit) qs.set("limit", limit);
    const query = qs.toString() ? `?${qs.toString()}` : "";
    const data = await serverGetJson(`/api/v1/posts${query}`);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const body = await req.json();
    const data = await serverPostJson("/api/v1/posts", body, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

