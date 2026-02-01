import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { serverPostJson } from "@/app/api/_lib/serverApi";

const COOKIE_TOKEN = "agora_access_token";
const COOKIE_ADDR = "agora_address";

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const body = (await req.json()) as { address?: string; signature?: string };
    const address = String(body?.address ?? "");
    const signature = String(body?.signature ?? "");
    const data = await serverPostJson<{ access_token: string; token_type: string }>("/api/v1/agents/auth/verify", {
      address,
      signature,
    });

    const token = String(data.access_token || "");
    if (!token) throw new Error("missing access_token");

    const secure = process.env.NODE_ENV === "production" || process.env.AGORA_COOKIE_SECURE === "1";
    const maxAge = 60 * 60 * 24; // 1 day (server default); keep conservative
    const sameSite = (process.env.AGORA_COOKIE_SAMESITE || "strict") as "strict" | "lax" | "none";

    const jar = await cookies();
    jar.set(COOKIE_TOKEN, token, {
      httpOnly: true,
      secure,
      sameSite,
      path: "/",
      maxAge,
    });
    jar.set(COOKIE_ADDR, address, {
      httpOnly: true,
      secure,
      sameSite,
      path: "/",
      maxAge,
    });

    return NextResponse.json({ ok: true, address });
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Unauthorized" }, { status: 401 });
  }
}

