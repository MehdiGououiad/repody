import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    /** Short-lived Keycloak access token for server/proxy API calls. */
    accessToken?: string;
    roles?: string[];
    error?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    roles?: string[];
    error?: string;
  }
}

export type { DefaultSession };
