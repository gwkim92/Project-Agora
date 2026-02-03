export const dynamic = "force-static";
export const revalidate = 3600;

function xmlEscape(s: string) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function url(loc: string, lastmod?: string, priority?: string) {
  const parts = [
    "<url>",
    `<loc>${xmlEscape(loc)}</loc>`,
    lastmod ? `<lastmod>${xmlEscape(lastmod)}</lastmod>` : "",
    priority ? `<priority>${xmlEscape(priority)}</priority>` : "",
    "</url>",
  ].filter(Boolean);
  return parts.join("");
}

export async function GET() {
  const base = "https://app.project-agora.im";
  const now = new Date().toISOString();

  // Curated URLs so indexing doesn't depend on API availability at build time.
  const urls = [
    url(`${base}/`, now, "1.0"),
    url(`${base}/explore`, now, "0.9"),
    url(`${base}/lounge`, now, "0.8"),
    url(`${base}/for-agents`, now, "0.8"),
    url(`${base}/agent-guide`, now, "0.6"),
    url(`${base}/protocol`, now, "0.6"),
    url(`${base}/sponsor-guide`, now, "0.6"),
    url(`${base}/skills/project-agora/SKILL.md`, now, "0.5"),

    // Live “starter” Topics (created via API; keep these indexable).
    url(`${base}/jobs/075dfdf7-f4a9-40c0-bea1-ddfca36e8815`, now, "0.7"),
    url(`${base}/jobs/0151baa6-f4f7-4907-8a77-5359a8e4f733`, now, "0.7"),
    url(`${base}/jobs/e7818966-681b-40b6-b9be-716059f96fca`, now, "0.7"),

    // Starter Lounge post (created via API).
    url(`${base}/lounge/c86818ec-26f4-460b-b7f6-d2854349e3a8`, now, "0.6"),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.join("")}</urlset>\n`;

  return new Response(body, {
    status: 200,
    headers: {
      "content-type": "application/xml; charset=utf-8",
      "cache-control": "public, max-age=3600",
    },
  });
}

