import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const allowedDevOrigins = [
  "127.0.0.1",
  "localhost",
  ...(process.env.NEXT_ALLOWED_DEV_ORIGINS?.split(",")
    .map((origin) => origin.trim())
    .filter(Boolean) ?? []),
];

const nextConfig: NextConfig = {
  output: "standalone",
  // Next 16 blocks cross-origin HMR when UI is opened as 127.0.0.1 vs localhost.
  allowedDevOrigins,
  experimental: {
    // lucide-react + recharts are already in Next's default optimize list.
    optimizePackageImports: [
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-select",
      "@radix-ui/react-tabs",
      "@radix-ui/react-tooltip",
      "cmdk",
    ],
  },
  // /api/v1/* is proxied at runtime by app/api/v1/[...path]/route.ts using
  // INTERNAL_API_URL (Compose: http://api:8000, K8s: http://repody-api:8000).
  // Do not bake BACKEND_URL into rewrites — that breaks portable Hub images.
  async redirects() {
    return [
      {
        source: "/",
        destination: "/dashboard",
        permanent: false,
      },
    ];
  },
};

// Official @sentry/nextjs build wrapper. Source-map upload disabled — Bugsink
// is Sentry-SDK-compatible for events but not SaaS map upload.
export default withSentryConfig(withNextIntl(nextConfig), {
  silent: true,
  sourcemaps: { disable: true },
});
