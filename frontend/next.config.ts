import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    // pdfjs-dist optionally requires canvas which isn't available in the browser
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
