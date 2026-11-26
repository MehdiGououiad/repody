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
  poweredByHeader: false,
  // Next 16 blocks cross-origin HMR when UI is opened as 127.0.0.1 vs localhost.
  allowedDevOrigins,
  experimental: {
    // Proxy buffers request bodies and truncates past this size (default 10mb). Multipart
    // run submissions carry several documents of up to AUDIT_MAX_UPLOAD_BYTES (25mb) each: keep
    // it at the API's AUDIT_MAX_REQUEST_BYTES (100 MiB), the largest request either accepts.
    proxyClientMaxBodySize: "100mb",
    // A run upload goes through the /api/v1 rewrite; allow it as long as the browser does.
    proxyTimeout: 120_000,
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
          // No framing, plugins or <base> tricks. Scripts, images and styles are not restricted
          // here: the brand logo is any URL set at runtime, and model-written Markdown renders no
          // images (document-markdown-preview.tsx).
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          // HTTPS only for a year, on every subdomain (the app is never served over HTTP).
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
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
  // Errors only (Bugsink keeps no traces or replays): the SDK's tree-shaking flags drop the rest
  // from the bundle, for Turbopack too (@sentry/nextjs `bundleSizeOptimizations`).
  bundleSizeOptimizations: {
    excludeDebugStatements: true,
    excludeTracing: true,
    excludeReplayIframe: true,
    excludeReplayShadowDom: true,
    excludeReplayWorker: true,
  },
});
