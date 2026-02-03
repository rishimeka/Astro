import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  transpilePackages: ['astrix-labs-uitk'],
};

export default nextConfig;
