"use client";

import { usePlatformAuthContext } from "@/components/auth/platform-auth";

export type PlatformAuthState = {
  /** Keycloak sign-in is available (Auth.js provider configured). */
  oidcEnabled: boolean;
  /** Auth.js has a Keycloak provider (env vars present). */
  keycloakConfigured: boolean;
  loading: boolean;
};

/**
 * Prefer RSC-injected PlatformAuthProvider (no client network on mount).
 * Falls back to "not configured" outside the provider (tests / edge cases).
 */
export function usePlatformAuth(): PlatformAuthState {
  const fromProvider = usePlatformAuthContext();
  if (fromProvider) return fromProvider;
  return { oidcEnabled: false, keycloakConfigured: false, loading: false };
}
