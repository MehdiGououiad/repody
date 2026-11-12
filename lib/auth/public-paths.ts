export const PUBLIC_PAGE_PATHS = ["/login", "/logout", "/unauthorized"] as const;

export const PUBLIC_API_PREFIXES = ["/api/auth", "/api/v1/healthz"] as const;

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

/** Where to go after signing in: a same-origin path from `callbackUrl`, else the dashboard. */
export function safeCallbackUrl(raw: string | null | undefined): string {
  return raw?.startsWith("/") && !raw.startsWith("//") ? raw : "/dashboard";
}
