export const PUBLIC_PAGE_PATHS = ["/login", "/unauthorized"] as const;

export const PUBLIC_API_PREFIXES = [
  "/api/auth",
  "/api/v1/healthz",
  "/api/v1/models/catalog",
] as const;

export function isPublicPage(path: string): boolean {
  return PUBLIC_PAGE_PATHS.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`)
  );
}

export function isPublicApi(path: string): boolean {
  return PUBLIC_API_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`)
  );
}
