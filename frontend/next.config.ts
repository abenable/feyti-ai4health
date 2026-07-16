import type { NextConfig } from "next";

// Backend is reached server-side (never from the browser), so it need not be
// exposed. In Docker this is the internal service URL (http://backend:8000);
// for local dev it defaults to the backend on localhost. Baked at build time.
const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/health", destination: `${BACKEND}/health` },
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
    ];
  },
};

export default nextConfig;
