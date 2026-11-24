import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow a local dev server to keep its own build output so a concurrent
  // `next build` (which deletes `.next`) cannot corrupt the running dev server.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  reactStrictMode: true,
  images: {
    domains: ["assets.studentradar.dev", "avatars.githubusercontent.com", "lh3.googleusercontent.com"],
  },
};

export default nextConfig;

