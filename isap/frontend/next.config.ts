import type { NextConfig } from "next";

const backendUrl = (process.env.INTERNAL_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
	  allowedDevOrigins: ["127.0.0.1", "localhost"],
  skipTrailingSlashRedirect: true,
  reactStrictMode: false,
  async rewrites() {
    return [
      { source: "/api/v1/pmla", destination: `${backendUrl}/api/v1/pmla/` },
      { source: "/api/v1/directories/pasf", destination: `${backendUrl}/api/v1/directories/pasf/` },
      { source: "/api/v1/directories/emergency-services", destination: `${backendUrl}/api/v1/directories/emergency-services/` },
      { source: "/api/:path*/", destination: `${backendUrl}/api/:path*/` },
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/health", destination: `${backendUrl}/health` },
    ];
  },
};

export default nextConfig;
