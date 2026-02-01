import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const COOKIE_TOKEN = "agora_access_token";
const COOKIE_ADDR = "agora_address";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(COOKIE_TOKEN)?.value ?? null;
  const address = jar.get(COOKIE_ADDR)?.value ?? null;
  return NextResponse.json({ authenticated: Boolean(token), address });
}

