import { NextRequest } from "next/server";

// Basic CSRF guard: ensure same-origin POSTs when cookies are involved.
// In dev, Origin might be absent for some tools; allow missing Origin.
export function assertSameOrigin(req: NextRequest) {
  const origin = req.headers.get("origin");
  if (!origin) return;
  const host = req.headers.get("host");
  if (!host) throw new Error("missing host");
  const expected = `http://${host}`;
  const expectedHttps = `https://${host}`;
  if (origin !== expected && origin !== expectedHttps) {
    throw new Error(`bad origin: ${origin}`);
  }
}

