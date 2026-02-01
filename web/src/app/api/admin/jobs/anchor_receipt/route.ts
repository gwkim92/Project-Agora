import { NextRequest, NextResponse } from "next/server";

import { assertSameOrigin } from "@/app/api/_lib/security";
import { getAccessTokenFromCookie } from "@/app/api/_lib/authCookies";
import { hasAdminAccessCookie } from "@/app/api/_lib/adminAccessCookies";
import { serverPostJson } from "@/app/api/_lib/serverApi";

export async function POST(req: NextRequest) {
  try {
    assertSameOrigin(req);
    const ok = await hasAdminAccessCookie();
    if (!ok) return NextResponse.json({ detail: "Admin signature required" }, { status: 401 });
    const token = await getAccessTokenFromCookie();
    if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
    const body = (await req.json()) as {
      job_id: string;
      anchor_tx_hash: string;
      anchor_chain_id: number;
      anchor_contract_address: string;
      anchor_block_number: number;
      anchor_log_index: number;
    };
    if (!body?.job_id) return NextResponse.json({ detail: "job_id is required" }, { status: 400 });
    const { job_id, ...rest } = body;
    const data = await serverPostJson(`/api/v1/jobs/${encodeURIComponent(job_id)}/anchor_receipt`, rest, { token });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ detail: e instanceof Error ? e.message : "Bad Request" }, { status: 400 });
  }
}

