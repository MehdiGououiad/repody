export const PUBLIC_PAGE_PATHS = ["/login", "/logout", "/unauthorized"] as const;

export const PUBLIC_API_PREFIXES = ["/api/auth", "/api/v1/healthz"] as const;

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
