import { realmRolesFromAccessToken } from "@/lib/auth/jwt-claims";

export type RefreshableJwt = {
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: number;
  roles?: string[];
  error?: string;
};

export async function refreshKeycloakAccessToken(
  token: RefreshableJwt
): Promise<RefreshableJwt> {
  const issuer =
    process.env.AUTH_KEYCLOAK_INTERNAL_ISSUER ?? process.env.AUTH_KEYCLOAK_ISSUER;
  const clientId = process.env.AUTH_KEYCLOAK_ID;
  const clientSecret =
    process.env.AUTH_KEYCLOAK_SECRET ?? process.env.AUTH_KEYCLOAK_CLIENT_SECRET;

  if (!issuer || !clientId || !token.refreshToken) {
    return { ...token, error: "RefreshTokenError" };
  }

  try {
    const res = await fetch(`${issuer}/protocol/openid-connect/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      signal: AbortSignal.timeout(8_000),
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret ?? "",
        grant_type: "refresh_token",
        refresh_token: token.refreshToken,
      }),
    });

    const data = (await res.json()) as {
      access_token?: string;
      refresh_token?: string;
      expires_in?: number;
      error_description?: string;
    };

    if (!res.ok || !data.access_token) {
      throw new Error(data.error_description ?? "Token refresh failed");
    }

    return {
      ...token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token ?? token.refreshToken,
      expiresAt: Math.floor(Date.now() / 1000) + (data.expires_in ?? 300),
      roles: realmRolesFromAccessToken(data.access_token),
      error: undefined,
    };
  } catch {
    return { ...token, error: "RefreshTokenError" };
  }
}
