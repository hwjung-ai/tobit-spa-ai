import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  typescript: {
    ignoreBuildErrors: true,
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
