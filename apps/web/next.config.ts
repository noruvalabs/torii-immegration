import type { NextConfig } from "next";

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
    return [{ source: "/backend/:path*", destination: `${apiBase}/:path*` }];
  },
};

export default nextConfig;
