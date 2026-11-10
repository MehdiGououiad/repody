import { decodeJwt } from "jose";

/** The roles the API grants (`repody/infra/auth.py`), in its precedence order. */
const APP_ROLES = ["platform_admin", "admin", "operator", "viewer"];

/**
 * The app roles of a Keycloak access token, read the way the API reads them: realm roles and
 * groups. Claims only: the API verifies the signature; a malformed token has no roles.
 */
export function rolesFromAccessToken(token: string | undefined): string[] {
  if (!token) return [];
  let claims: { realm_access?: { roles?: unknown[] }; groups?: unknown[] };
  try {
    claims = decodeJwt(token);
  } catch {
    return [];
  }
  const granted = new Set(
    [...(claims.realm_access?.roles ?? []), ...(claims.groups ?? [])].map((role) =>
      String(role).replace(/^\//, "")
    )
  );
  return APP_ROLES.filter((role) => granted.has(role));
}
