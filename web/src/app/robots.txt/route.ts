export const dynamic = "force-static";

export async function GET() {
  const body = [
    "User-agent: *",
    "Allow: /",
    "",
    "Sitemap: https://app.project-agora.im/sitemap.xml",
    "",
  ].join("\n");

  return new Response(body, {
    status: 200,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=3600",
    },
  });
}

