import { withSentryConfig } from "@sentry/nextjs/config";
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
    // Proxy buffers request bodies and truncates past this size (default 10mb). Multipart
    // run submissions carry several documents of up to AUDIT_MAX_UPLOAD_BYTES (25mb) each.
    proxyClientMaxBodySize: "100mb",
    // A run upload goes through the /api/v1 rewrite; allow it as long as the browser does.
    proxyTimeout: 120_000,
    // lucide-react and recharts are already in Next's default optimize list.
    optimizePackageImports: ["radix-ui", "cmdk"],
  },
  // /api/v1/* is rewritten at runtime by proxy.ts to INTERNAL_API_URL (Compose: http://api:8000,
  // K8s: http://repody-api:8000). Do not bake it into rewrites: images must stay portable.
  // Browser protections for every page: no framing (clickjacking on publish and delete), no
  // MIME sniffing, no full URLs (report ids) in the Referer sent to other sites.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
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

// Official @sentry/nextjs build wrapper. Source-map upload disabled - Bugsink
// is Sentry-SDK-compatible for events but not SaaS map upload.
export default withSentryConfig(withNextIntl(nextConfig), {
  silent: true,
  sourcemaps: { disable: true },
});
