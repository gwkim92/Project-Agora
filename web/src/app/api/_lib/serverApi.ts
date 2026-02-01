// Prefer server-only env, fallback to public env for convenience.
const API_BASE = (
  process.env.AGORA_API_BASE ??
  process.env.NEXT_PUBLIC_AGORA_API_BASE ??
  "https://api.project-agora.im"
).replace(/\/$/, "");

export async function serverPostJson<T>(path: string, body: unknown, opts?: { token?: string | null }) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(opts?.token ? { Authorization: `Bearer ${opts.token}` } : {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as T;
}

export async function serverPutJson<T>(path: string, body: unknown, opts?: { token?: string | null }) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(opts?.token ? { Authorization: `Bearer ${opts.token}` } : {}),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`PUT ${path} failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as T;
}

export async function serverGetJson<T>(path: string, opts?: { token?: string | null }) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: {
      ...(opts?.token ? { Authorization: `Bearer ${opts.token}` } : {}),
    },
    cache: "no-store",
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as T;
}

