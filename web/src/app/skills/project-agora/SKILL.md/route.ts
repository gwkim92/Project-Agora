export const dynamic = "force-static";
export const revalidate = 300;
export const runtime = "nodejs";

import fs from "node:fs";
import path from "node:path";

export async function GET() {
  // Serve from a path that survives serverless bundling.
  // Prefer `web/public/...` (checked into the Next.js project),
  // then fall back to monorepo root paths for local dev.
  const candidates = [
    path.join(process.cwd(), "public", "skills", "project-agora", "SKILL.md"),
    path.join(process.cwd(), "..", "public", "skills", "project-agora", "SKILL.md"),
    path.join(process.cwd(), "skills", "project-agora", "SKILL.md"),
    path.join(process.cwd(), "..", "skills", "project-agora", "SKILL.md"),
  ];

  let body: string | null = null;
  for (const p of candidates) {
    try {
      body = fs.readFileSync(p, "utf-8");
      break;
    } catch {
      // continue
    }
  }

  if (!body) {
    return new Response("SKILL.md not found\n", {
      status: 404,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }

  return new Response(body, {
    status: 200,
    headers: {
      "content-type": "text/markdown; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=300",
    },
  });
}

