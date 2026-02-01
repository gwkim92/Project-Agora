import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

function buildCsp() {
  // Note: We use inline styles in UI (style=...) so style-src needs 'unsafe-inline'.
  // In dev, Next uses eval for HMR.
  // In dev, Next also injects inline scripts for bootstrapping/hydration.
  // If we block those, dev hydration breaks (and can trigger Next invariant errors).
  const scriptSrc = isProd ? "script-src 'self'" : "script-src 'self' 'unsafe-eval' 'unsafe-inline'";
  return [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self' http://127.0.0.1:8000 http://localhost:8000",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

const nextConfig: NextConfig = {
  // Fix dev warning:
  // "Cross origin request detected from 127.0.0.1 to /_next/* resource..."
  // Allow local dev origins explicitly.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
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
