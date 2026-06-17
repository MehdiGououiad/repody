const APP_ROLES = new Set(["platform_admin", "admin", "operator", "viewer"]);

export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const json =
      typeof Buffer !== "undefined"
        ? Buffer.from(padded, "base64").toString("utf8")
        : atob(padded);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function realmRolesFromAccessToken(token: string | undefined): string[] {
  if (!token) return [];
  const payload = decodeJwtPayload(token);
  const realmAccess = payload?.realm_access as { roles?: string[] } | undefined;
  const roles = realmAccess?.roles ?? [];
  return roles.filter((role) => APP_ROLES.has(role)).sort();
}

export function initialsFromSession(name?: string | null, email?: string | null): string {
  const source = (name?.trim() || email?.trim() || "?").replace(/@.+$/, "");
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}
