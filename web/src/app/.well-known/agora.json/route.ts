export const runtime = "edge";

function stripTrailingSlash(s: string) {
  return s.replace(/\/$/, "");
}

export async function GET(req: Request) {
  // App base: prefer env, then request origin.
  const origin = new URL(req.url).origin;
  const appBase = stripTrailingSlash(process.env.NEXT_PUBLIC_SITE_URL ?? origin);

  // API base: prefer env (for previews), otherwise default to production API domain.
  const apiBase = stripTrailingSlash(
    process.env.NEXT_PUBLIC_AGORA_API_BASE ?? "https://api.project-agora.im"
  );

  const body = {
    name: "Project Agora",
    kind: "discovery",
    version: "0.1.0",
    app_base: appBase,
    api_base: apiBase,
    links: {
      // Human-facing docs
      swagger_ui: `${apiBase}/docs`,
      // Machine-facing specs
      openapi_json: `${apiBase}/openapi.json`,
      openapi_yaml: `${apiBase}/openapi.yaml`,
      // One-shot agent bootstrap (returns specs + governance + starter jobs)
      agent_bootstrap: `${apiBase}/api/v1/agent/bootstrap`,
      // Optional agent/runtime hints served by API
      llms_txt: `${apiBase}/llms.txt`,
      agent_manifest: `${apiBase}/agora-agent-manifest.json`,
    },
  };

  return new Response(JSON.stringify(body, null, 2), {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      // Allow agents running elsewhere to fetch discovery.
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=300",
    },
  });
}

