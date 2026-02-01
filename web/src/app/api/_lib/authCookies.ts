import { cookies } from "next/headers";

const COOKIE_TOKEN = "agora_access_token";

export async function getAccessTokenFromCookie(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(COOKIE_TOKEN)?.value ?? null;
}

