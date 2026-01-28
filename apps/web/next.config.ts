import type { NextConfig } from "next";

// API Base URL configuration with fallback
const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

console.log(`[Next.js Config] API_BASE_URL: ${API_BASE_URL}`);

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    // Validate API_BASE_URL
    try {
      const apiUrl = new URL(API_BASE_URL);
      console.log(`[Next.js Rewrites] Proxying to: ${apiUrl.href}`);
    } catch (error) {
      console.error(`[Next.js Rewrites] Invalid API_BASE_URL: ${API_BASE_URL}`);
      throw new Error(`Invalid API_BASE_URL: ${API_BASE_URL}`);
    }

    return [
      // Proxy all API requests to backend
      {
        source: "/api/:path*",
        destination: `${API_BASE_URL}/api/:path*`,
      },
      // Proxy auth requests
      {
        source: "/auth/:path*",
        destination: `${API_BASE_URL}/auth/:path*`,
      },
      // Proxy health check
      {
        source: "/health",
        destination: `${API_BASE_URL}/health`,
      },
      // Proxy history endpoint
      {
        source: "/history",
        destination: `${API_BASE_URL}/history`,
      },
      {
        source: "/history/:path*",
        destination: `${API_BASE_URL}/history/:path*`,
      },
      // Proxy ops routes
      {
        source: "/ops/:path*",
        destination: `${API_BASE_URL}/ops/:path*`,
      },
      // Proxy admin/module routes
      {
        source: "/admin/:path*",
        destination: `${API_BASE_URL}/admin/:path*`,
      },
      // Proxy asset registry
      {
        source: "/asset-registry/:path*",
        destination: `${API_BASE_URL}/asset-registry/:path*`,
      },
      // Proxy api-manager routes
      {
        source: "/api-manager/:path*",
        destination: `${API_BASE_URL}/api-manager/:path*`,
      },
      // Proxy inspector routes
      {
        source: "/inspector/:path*",
        destination: `${API_BASE_URL}/inspector/:path*`,
      },
      // Proxy cep-builder routes
      {
        source: "/cep-builder/:path*",
        destination: `${API_BASE_URL}/cep-builder/:path*`,
      },
      // Proxy CEP routes
      {
        source: "/cep/:path*",
        destination: `${API_BASE_URL}/cep/:path*`,
      },
      // Proxy UI builder routes
      {
        source: "/ui-builder/:path*",
        destination: `${API_BASE_URL}/ui-builder/:path*`,
      },
      // Proxy threads routes
      {
        source: "/threads/:path*",
        destination: `${API_BASE_URL}/threads/:path*`,
      },
      // Proxy documents routes
      {
        source: "/documents",
        destination: `${API_BASE_URL}/documents`,
      },
      {
        source: "/documents/:path*",
        destination: `${API_BASE_URL}/documents/:path*`,
      },
      // Proxy chat routes
      {
        source: "/chat/:path*",
        destination: `${API_BASE_URL}/chat/:path*`,
      },
      // Proxy permissions routes
      {
        source: "/permissions/:path*",
        destination: `${API_BASE_URL}/permissions/:path*`,
      },
      // Proxy settings routes
      {
        source: "/settings/:path*",
        destination: `${API_BASE_URL}/settings/:path*`,
      },
      // Proxy audit-log routes
      {
        source: "/audit-log/:path*",
        destination: `${API_BASE_URL}/audit-log/:path*`,
      },
      // Proxy api-keys routes
      {
        source: "/api-keys/:path*",
        destination: `${API_BASE_URL}/api-keys/:path*`,
      },
    ];
  },
  redirects: async () => {
    return [
      // Redirect Data module routes to Admin module
      {
        source: "/data",
        destination: "/admin/explorer",
        permanent: true,
      },
      {
        source: "/data/sources",
        destination: "/admin/assets?type=source",
        permanent: true,
      },
      {
        source: "/data/catalog",
        destination: "/admin/assets?type=schema",
        permanent: true,
      },
      {
        source: "/data/resolvers",
        destination: "/admin/assets?type=resolver",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
