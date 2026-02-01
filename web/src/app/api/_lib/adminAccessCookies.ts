import { cookies } from "next/headers";

const COOKIE_ADMIN_ACCESS = "agora_admin_access";

export async function hasAdminAccessCookie(): Promise<boolean> {
  const jar = await cookies();
  return jar.get(COOKIE_ADMIN_ACCESS)?.value === "1";
}

export function setAdminAccessCookie(resp: Response, ttlSeconds: number) {
  // NextResponse has cookies.set; but in case we ever pass a raw Response, we keep this file focused on helpers.
  // This is a placeholder to keep imports consistent (we set cookies in route.ts directly).
  void resp;
  void ttlSeconds;
}

export const ADMIN_ACCESS_COOKIE_NAME = COOKIE_ADMIN_ACCESS;

