import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";
import { NextResponse } from "next/server";
import { realmRolesFromAccessToken } from "@/lib/auth/jwt-claims";
import { isPublicPage } from "@/lib/auth/public-paths";
import { refreshKeycloakAccessToken } from "@/lib/auth/refresh-keycloak-token";

const keycloakIssuer = process.env.AUTH_KEYCLOAK_ISSUER;
const keycloakClientSecret =
  process.env.AUTH_KEYCLOAK_SECRET ?? process.env.AUTH_KEYCLOAK_CLIENT_SECRET;
const apiOidcExplicitlyDisabled = process.env.AUDIT_OIDC_ENABLED === "false";
const keycloakConfigured = Boolean(
  !apiOidcExplicitlyDisabled &&
    keycloakIssuer &&
    process.env.AUTH_KEYCLOAK_ID &&
    process.env.AUTH_SECRET
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
  providers: keycloakConfigured
    ? [
        Keycloak({
          clientId: process.env.AUTH_KEYCLOAK_ID!,
          clientSecret: keycloakClientSecret ?? "",
          issuer: keycloakIssuer!,
          authorization: {
            params: { scope: keycloakScopes },
          },
        }),
      ]
    : [],
  callbacks: {
    authorized({ auth: session, request }) {
      if (!keycloakConfigured) {
        return true;
      }

      const path = request.nextUrl.pathname;

      if (path.startsWith("/api/")) {
        return true;
      }

      if (isPublicPage(path)) {
        if (path === "/login" && session?.user && !session.error) {
          const callback = request.nextUrl.searchParams.get("callbackUrl");
          const dest =
            callback && callback.startsWith("/") && !callback.startsWith("//")
              ? callback
              : "/dashboard";
          return NextResponse.redirect(new URL(dest, request.url));
        }
        return true;
      }

      return Boolean(session?.user && !session.error);
    },
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at;
        token.roles = realmRolesFromAccessToken(account.access_token);
        return token;
      }

      const expiresAt = token.expiresAt;
      if (typeof expiresAt === "number" && Date.now() / 1000 < expiresAt - 60) {
        return token;
      }

      if (token.refreshToken) {
        const refreshed = await refreshKeycloakAccessToken({
          accessToken: token.accessToken as string | undefined,
          refreshToken: token.refreshToken as string | undefined,
          expiresAt: token.expiresAt as number | undefined,
          roles: token.roles as string[] | undefined,
          error: token.error as string | undefined,
        });
        return { ...token, ...refreshed };
      }

      return token;
    },
    async session({ session, token }) {
      if (token.error) {
        session.error = token.error as string;
        return session;
      }
      if (token.accessToken) {
        session.accessToken = token.accessToken as string;
      }
      if (token.roles) {
        session.roles = token.roles as string[];
      }
      return session;
    },
  },
});

export function isOidcConfigured(): boolean {
  return keycloakConfigured;
}
