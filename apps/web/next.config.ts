import path from "node:path";
import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";

// Single env file for the whole monorepo (see /.env.example at the repo root) — Next.js only
// auto-loads .env files from this app's own directory, so load the root one explicitly before
// reading process.env below. We pass forceReload=true so the root .env is merged even if
// Next.js already ran an initial check on apps/web.
loadEnvConfig(
  path.resolve(import.meta.dirname, "../.."),
  process.env.NODE_ENV !== "production",
  undefined,
  true,
);

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (only the traced
  // server + its deps ship — see apps/web/Dockerfile).
  output: "standalone",
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
    NEXT_PUBLIC_PADDLE_CLIENT_TOKEN: process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN,
    NEXT_PUBLIC_PADDLE_ENV: process.env.NEXT_PUBLIC_PADDLE_ENV,
  },
  async rewrites() {
    // Browser calls to /api/* are proxied to the FastAPI system of record. In dev this
    // points at the local API; in the container the edge (nginx) owns the routing, so
    // this rewrite is a dev convenience. Set NEXT_PUBLIC_API_BASE_URL to override.
    const apiBase = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
    const aiBase = process.env.AI_PROXY_TARGET ?? "http://localhost:8001";
    return [
      { source: "/backend/:path*", destination: `${apiBase}/:path*` },
      { source: "/assistant/:path*", destination: `${aiBase}/:path*` },
    ];
  },
  async redirects() {
    return [
      { source: "/privacy-policy", destination: "/privacy", permanent: true },
      { source: "/terms-of-service", destination: "/terms", permanent: true },
      { source: "/refund-policy", destination: "/refund", permanent: true },
      { source: "/refunds", destination: "/refund", permanent: true },
      { source: "/cookie-policy", destination: "/cookies", permanent: true },
    ];
  },
};

export default nextConfig;
