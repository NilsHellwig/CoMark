import type { NextConfig } from "next";

// The browser talks to the API same-origin via /api/v1 (so the httpOnly session
// cookie is first-party); Next proxies it to the backend container/service.
const API_URL = process.env.API_URL ?? "http://localhost:8897";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: { root: import.meta.dirname },
  devIndicators: false,
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${API_URL}/api/v1/:path*` },
      { source: "/docs", destination: `${API_URL}/docs` },
    ];
  },
};

export default nextConfig;
