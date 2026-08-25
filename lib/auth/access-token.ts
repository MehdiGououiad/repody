import type { NextRequest } from "next/server";

/**
 * Prefer the access token already refreshed by the Auth.js `auth()` wrapper
 * (jwt → session). Do not call `getToken()` here — that reads the inbound
 * cookie and can race a second Keycloak refresh against the wrapper.
 */
export function getRequestAccessToken(
  request: NextRequest & {
    auth?: {
      accessToken?: string | null;
      error?: string | null;
    } | null;
  }
): string | undefined {
  if (request.auth?.error) {
    return undefined;
  }
  const accessToken = request.auth?.accessToken;
  return typeof accessToken === "string" && accessToken.length > 0
    ? accessToken
    : undefined;
}
