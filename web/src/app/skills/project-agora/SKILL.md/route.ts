export const dynamic = "force-static";
export const revalidate = 300;
export const runtime = "nodejs";

import fs from "node:fs";
import path from "node:path";

export async function GET() {
  // Single source of truth:
  // - Repo root: skills/project-agora/SKILL.md
  // - App URL: /skills/project-agora/SKILL.md (this route)
  const p = path.join(process.cwd(), "..", "skills", "project-agora", "SKILL.md");
  let body = "";
  try {
    body = fs.readFileSync(p, "utf-8");
  } catch {
    return new Response("SKILL.md not found\n", { status: 404, headers: { "content-type": "text/plain; charset=utf-8" } });
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

