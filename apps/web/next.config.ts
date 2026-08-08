import path from "node:path";
import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";

// Single env file for the whole monorepo (see /.env.example at the repo root) — Next.js only
// auto-loads .env files from this app's own directory, so load the root one explicitly before
// reading process.env below.
loadEnvConfig(path.resolve(import.meta.dirname, "../.."));

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (only the traced
  // server + its deps ship — see apps/web/Dockerfile).
  output: "standalone",
  reactStrictMode: true,
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
};

export default nextConfig;
