import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";
import { realmRolesFromAccessToken } from "@/lib/auth/jwt-claims";
import { refreshKeycloakAccessToken } from "@/lib/auth/refresh-keycloak-token";

const keycloakPublicIssuer = process.env.AUTH_KEYCLOAK_ISSUER;
const keycloakClientId = process.env.AUTH_KEYCLOAK_ID;
const keycloakServerIssuer = process.env.AUTH_KEYCLOAK_INTERNAL_ISSUER ?? keycloakPublicIssuer;
const keycloakClientSecret =
  process.env.AUTH_KEYCLOAK_SECRET ?? process.env.AUTH_KEYCLOAK_CLIENT_SECRET;
const apiOidcExplicitlyDisabled = process.env.AUDIT_OIDC_ENABLED === "false";
const keycloakConfigured = Boolean(
  !apiOidcExplicitlyDisabled && keycloakPublicIssuer && keycloakClientId && process.env.AUTH_SECRET
);
const keycloakScopes =
  process.env.AUTH_KEYCLOAK_OFFLINE_ACCESS === "true"
    ? "openid email profile offline_access"
    : "openid email profile";

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  secret: process.env.AUTH_SECRET,
  pages: {
    signIn: "/login",
    error: "/login",
  },
  // The extra truthiness checks repeat keycloakConfigured so the compiler can
  // narrow the two optional env values inside the branch.
  providers:
    keycloakConfigured && keycloakClientId && keycloakPublicIssuer
      ? [
          Keycloak({
            clientId: keycloakClientId,
            clientSecret: keycloakClientSecret ?? "",
            // JWT `iss` matches the public gateway hostname - not the in-cluster service name.
            issuer: keycloakPublicIssuer,
            wellKnown: `${keycloakServerIssuer}/.well-known/openid-configuration`,
            authorization: {
              url: `${keycloakPublicIssuer}/protocol/openid-connect/auth`,
              params: { scope: keycloakScopes },
            },
            token: `${keycloakServerIssuer}/protocol/openid-connect/token`,
            userinfo: `${keycloakServerIssuer}/protocol/openid-connect/userinfo`,
          }),
        ]
      : [],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at;
        token.roles = realmRolesFromAccessToken(account.access_token);
        return token;
      }

      if (token.expiresAt && Date.now() / 1000 < token.expiresAt - 60) return token;
      if (token.refreshToken) return refreshKeycloakAccessToken(token);
      return token.error ? token : { ...token, error: "SessionExpired" };
    },
    async session({ session, token }) {
      if (token.error || !token.accessToken) {
        session.error = token.error ?? "SessionExpired";
        return session;
      }
      // Proxy and Server Components call the API with the token Auth.js just refreshed.
      session.accessToken = token.accessToken;
      session.roles = token.roles;
      return session;
    },
  },
});

export function isOidcConfigured(): boolean {
  return keycloakConfigured;
}
