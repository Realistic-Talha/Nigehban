/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  experimental: {
    optimizeCss: false,
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
  transpilePackages: ["@nigehban/ui", "@nigehban/shared-types"],
  async redirects() {
    return [
      { source: "/scam-checker", destination: "/check/scam", permanent: true },
      { source: "/fact-check", destination: "/check/fact", permanent: true },
      { source: "/deepfake-checker", destination: "/check/media", permanent: true },
    ];
  },
};

export default nextConfig;
