export const AGORA_API_BASE =
  (process.env.NEXT_PUBLIC_AGORA_API_BASE ??
    // Server-side fallback (works in server components / route handlers on Vercel).
    process.env.AGORA_API_BASE ??
    "https://api.project-agora.im"
  ).replace(/\/$/, "");

// Demo default: Base Sepolia (84532). Production should set NEXT_PUBLIC_AGORA_CHAIN_ID explicitly.
export const AGORA_CHAIN_ID = Number(process.env.NEXT_PUBLIC_AGORA_CHAIN_ID ?? "84532");

export const AGORA_PUBLIC_SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ?? "";

