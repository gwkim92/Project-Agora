export const AGORA_API_BASE =
  process.env.NEXT_PUBLIC_AGORA_API_BASE?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export const AGORA_CHAIN_ID = Number(process.env.NEXT_PUBLIC_AGORA_CHAIN_ID ?? "8453");

export const AGORA_PUBLIC_SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ?? "";

