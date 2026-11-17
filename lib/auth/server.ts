import "server-only";

import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { genericOAuth } from "better-auth/plugins/generic-oauth";
import type { Account } from "@/lib/auth/account";

/**
 * Sign-in with Keycloak through Better Auth, stateless: no database. The session and the
 * Keycloak tokens live in encrypted cookies; Better Auth refreshes the access token when it is
 * about to expire (`accessToken`). https://www.better-auth.com/docs/concepts/session-management
 *
 * Every endpoint comes from Keycloak's discovery document. The server may fetch it in-cluster
 * (AUTH_KEYCLOAK_INTERNAL_ISSUER); Keycloak then names its server-to-server endpoints on that
 * host and the browser ones on its public URL (hostname v2, KC_HOSTNAME_BACKCHANNEL_DYNAMIC).
 */
const keycloak = {
  issuer: (process.env.AUTH_KEYCLOAK_INTERNAL_ISSUER ?? process.env.AUTH_KEYCLOAK_ISSUER)?.replace(
    /\/$/,
    ""
  ),
  clientId: process.env.AUTH_KEYCLOAK_ID,
  clientSecret: process.env.AUTH_KEYCLOAK_SECRET,
};

/** Sign-in is on when Keycloak and the session secret are set, unless the API runs without it. */
export const oidcEnabled = Boolean(
  process.env.AUDIT_OIDC_ENABLED !== "false" &&
    keycloak.issuer &&
    keycloak.clientId &&
    process.env.BETTER_AUTH_SECRET
);

const SESSION_SECONDS = 7 * 24 * 60 * 60;
export const KEYCLOAK = "keycloak";

export const auth = betterAuth({
  appName: "Repody",
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL,
  session: {
    expiresIn: SESSION_SECONDS,
    // Without a database the encrypted cookie is the session; it renews itself before expiry.
    cookieCache: { enabled: true, strategy: "jwe", maxAge: SESSION_SECONDS, refreshCache: true },
  },
  account: { storeStateStrategy: "cookie", storeAccountCookie: true },
  // Sign-in errors come back to the login page as `?error=<code>`.
  onAPIError: { errorURL: "/login" },
  plugins: [
    ...(oidcEnabled && keycloak.issuer && keycloak.clientId
      ? [
          genericOAuth({
            config: [
              {
                providerId: KEYCLOAK,
                discoveryUrl: `${keycloak.issuer}/.well-known/openid-configuration`,
                clientId: keycloak.clientId,
                clientSecret: keycloak.clientSecret,
                scopes: ["openid", "email", "profile"],
                pkce: true,
              },
            ],
          }),
        ]
      : []),
    nextCookies(), // Server actions can set the session cookies.
  ],
});

/** The signed-in user's session, or null (also when sign-in is off). */
export async function session(headers: Headers) {
  if (!oidcEnabled) return null;
  return auth.api.getSession({ headers }).catch(() => null);
}

/**
 * A valid Keycloak access token for the request's session, refreshed if it was about to expire,
 * with the cookies that carry the refreshed tokens (`setCookies`, empty when nothing changed).
 * Null without a usable session.
 */
export async function accessToken(
  headers: Headers
): Promise<{ token: string; setCookies: string[] } | null> {
  if (!oidcEnabled) return null;
  try {
    const { headers: responseHeaders, response } = await auth.api.getAccessToken({
      body: { useAccountCookie: true }, // the Keycloak tokens in the encrypted account cookie
      headers,
      returnHeaders: true,
    });
    if (!response.accessToken) return null;
    return { token: response.accessToken, setCookies: responseHeaders.getSetCookie() };
  } catch {
    return null;
  }
}

/** Who is signed in, as the app shell shows them (their roles come from `GET /v1/me`). */
export async function currentAccount(headers: Headers): Promise<Account | null> {
  const current = await session(headers);
  if (!current) return null;
  return { name: current.user.name || null, email: current.user.email || null };
}
