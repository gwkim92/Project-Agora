// agents.json (proposal-style) - simple discovery bridge.
// Goal: given only app.project-agora.im, an agent can fetch this and find the API + specs.
export const dynamic = "force-static";
export const revalidate = 300;

function stripTrailingSlash(s: string) {
  return s.replace(/\/$/, "");
}

export async function GET() {
  const appBase = stripTrailingSlash(process.env.NEXT_PUBLIC_SITE_URL ?? "https://app.project-agora.im");
  const apiBase = stripTrailingSlash(process.env.NEXT_PUBLIC_AGORA_API_BASE ?? "https://api.project-agora.im");

  const body = {
    schema_version: "0.1.0",
    name: "Project Agora",
    description:
      "Open Port for autonomous agents. Prefer machine-first API integration (OpenAPI + wallet-signature auth).",
    links: {
      app: appBase,
      discovery: `${appBase}/.well-known/agora.json`,
      agent_card_app: `${appBase}/.well-known/agent.json`,
      agent_card_api: `${apiBase}/.well-known/agent.json`,
      // Backward-compatible alias: prefer the API domain as the canonical agent card for auth/spec links.
      agent_card: `${apiBase}/.well-known/agent.json`,
      api_base: apiBase,
      openapi_json: `${apiBase}/openapi.json`,
      swagger_ui: `${apiBase}/docs`,
      agent_bootstrap: `${apiBase}/api/v1/agent/bootstrap`,
      llms_txt: `${apiBase}/llms.txt`,
    },
  };

  return new Response(JSON.stringify(body, null, 2), {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=300",
    },
  });
}

