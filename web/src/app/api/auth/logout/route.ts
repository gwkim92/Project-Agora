import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

import { assertSameOrigin } from "@/app/api/_lib/security";

const COOKIE_TOKEN = "agora_access_token";
const COOKIE_ADDR = "agora_address";

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const secure = process.env.NODE_ENV === "production" || process.env.AGORA_COOKIE_SECURE === "1";
    const sameSite = (process.env.AGORA_COOKIE_SAMESITE || "strict") as "strict" | "lax" | "none";
    const jar = await cookies();
    jar.set(COOKIE_TOKEN, "", { httpOnly: true, secure, sameSite, path: "/", maxAge: 0 });
    jar.set(COOKIE_ADDR, "", { httpOnly: true, secure, sameSite, path: "/", maxAge: 0 });
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

