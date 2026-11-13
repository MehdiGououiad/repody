import type { NextConfig } from "next";

/** repody.com: a static export (HTML, CSS, JS, images), served from a CDN. */
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  // The site has its own lockfile inside the product's repository; Next would otherwise pick the outer one as the root.
  turbopack: { root: import.meta.dirname },
  // One 404 for the two root layouts (app/(root) and app/[locale]).
  experimental: { globalNotFound: true },
};

export default nextConfig;
