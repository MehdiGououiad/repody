import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";
import { realmRolesFromAccessToken } from "@/lib/auth/jwt-claims";

const keycloakIssuer = process.env.AUTH_KEYCLOAK_ISSUER;
const keycloakClientSecret =
  process.env.AUTH_KEYCLOAK_SECRET ?? process.env.AUTH_KEYCLOAK_CLIENT_SECRET;
const keycloakConfigured = Boolean(
  keycloakIssuer && process.env.AUTH_KEYCLOAK_ID && process.env.AUTH_SECRET
);

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
        }),
      ]
    : [],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.roles = realmRolesFromAccessToken(account.access_token);
      }
      return token;
    },
    async session({ session, token }) {
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
