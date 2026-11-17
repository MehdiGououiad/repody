export const PUBLIC_PAGE_PATHS = ["/login", "/logout", "/unauthorized"] as const;

/** No session: sign-in itself, the health check, and the site's access requests (checked by the
 * API: anti-robot token, a limit per network, CORS for the site's origin). */
export const PUBLIC_API_PREFIXES = [
  "/api/auth",
  "/api/v1/healthz",
  "/api/v1/access-requests",
] as const;

/** The API calls a workflow API key may make without a session: start a run of its workflow,
 * then read that run (status, then the audit report). The API checks the key itself. */
const WORKFLOW_KEY_ROUTES: ReadonlyArray<{ method: string; path: RegExp }> = [
  { method: "POST", path: /^\/api\/v1\/workflows\/[^/]+\/runs$/ },
  { method: "GET", path: /^\/api\/v1\/runs\/[^/]+$/ },
];

export function acceptsWorkflowKey(method: string, path: string): boolean {
  return WORKFLOW_KEY_ROUTES.some((route) => route.method === method && route.path.test(path));
}

export function isPublicPage(path: string): boolean {
  return PUBLIC_PAGE_PATHS.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

export function isPublicApi(path: string): boolean {
  return PUBLIC_API_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

const SAME_ORIGIN = "https://same-origin.invalid";

/** Where to go after signing in: a same-origin path from `callbackUrl`, else the dashboard.
 * The path is resolved as a browser would: URL parsing drops tabs and newlines and reads `\` as
 * `/`, so `/\evil.com` or `/<tab>/evil.com` would leave the site. Only what stays on the origin
 * is kept, in its parsed form. */
export function safeCallbackUrl(raw: string | null | undefined): string {
  if (!raw?.startsWith("/")) return "/dashboard";
  try {
    const url = new URL(raw, SAME_ORIGIN);
    if (url.origin !== SAME_ORIGIN) return "/dashboard";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return "/dashboard";
  }
}
