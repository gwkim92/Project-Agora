import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { serverGetJson } from "@/app/api/_lib/serverApi";

export async function GET(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const url = new URL(req.url);
    const addresses = url.searchParams.get("addresses");
    if (!addresses) return NextResponse.json({ detail: "Missing addresses" }, { status: 400 });
    const data = await serverGetJson(`/api/v1/profiles?addresses=${encodeURIComponent(addresses)}`);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

