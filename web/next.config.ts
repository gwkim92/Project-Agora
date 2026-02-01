import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

function buildCsp() {
  // Note: We use inline styles in UI (style=...) so style-src needs 'unsafe-inline'.
  // In dev, Next uses eval for HMR.
  // In dev, Next also injects inline scripts for bootstrapping/hydration.
  // If we block those, dev hydration breaks (and can trigger Next invariant errors).
  // Vercel Analytics loads an external script from va.vercel-scripts.com and sends events to vitals.vercel-analytics.com.
  const scriptSrc = isProd
    // NOTE: Next.js uses inline scripts for bootstrapping/hydration; keep unsafe-inline in prod to avoid breaking client interactions.
    ? "script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com"
    : "script-src 'self' 'unsafe-eval' 'unsafe-inline'";

  const apiBase =
    (process.env.NEXT_PUBLIC_AGORA_API_BASE ??
      process.env.AGORA_API_BASE ??
      "https://api.project-agora.im").replace(/\/$/, "");

  // Connect-src must allow:
  // - our API base (browser fetches for auth/jobs/etc)
  // - Vercel Analytics collection endpoint
  // - WalletConnect endpoints (websocket + https)
  const connectSrcList = [
    "'self'",
    apiBase,
    "https://vitals.vercel-analytics.com",
    "https://vercel.live",
    "https://*.walletconnect.com",
    "https://*.walletconnect.org",
    "https://rpc.walletconnect.com",
    "https://rpc.walletconnect.org",
    "wss://*.walletconnect.com",
    "wss://*.walletconnect.org",
  ].join(" ");
  return [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connectSrcList}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

const nextConfig: NextConfig = {
  // Fix dev warning:
  // Allow local dev origins explicitly.
  allowedDevOrigins: ["localhost"],
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // Apply CSP in prod; dev needs relaxed CSP (or no CSP) to avoid breaking Next dev runtime.
          ...(isProd ? [{ key: "Content-Security-Policy", value: buildCsp() }] : []),
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          // COOP/CORP can interfere with certain dev tooling flows; keep them for prod hardening.
          ...(isProd ? [{ key: "Cross-Origin-Opener-Policy", value: "same-origin" }] : []),
          ...(isProd ? [{ key: "Cross-Origin-Resource-Policy", value: "same-origin" }] : []),
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
