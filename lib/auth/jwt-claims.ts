import { decodeJwt } from "jose";

const APP_ROLES = new Set(["platform_admin", "admin", "operator", "viewer"]);

export function realmRolesFromAccessToken(token: string | undefined): string[] {
  if (!token) return [];
  // Claims only (the API verifies the signature); jose throws on a malformed token.
  let realmAccess: { roles?: string[] } | undefined;
  try {
    realmAccess = decodeJwt(token).realm_access as { roles?: string[] } | undefined;
  } catch {
    return [];
  }
  const roles = realmAccess?.roles ?? [];
  return roles.filter((role) => APP_ROLES.has(role)).sort();
}

export function initialsFromSession(name?: string | null, email?: string | null): string {
  const source = (name?.trim() || email?.trim() || "?").replace(/@.+$/, "");
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]?.[0] ?? ""}${parts[1]?.[0] ?? ""}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}
