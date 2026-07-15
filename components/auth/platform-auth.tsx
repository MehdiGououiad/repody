"use client";

import { createContext, use } from "react";
import type { PlatformAuthState } from "@/lib/hooks/use-platform-auth";

const PlatformAuthContext = createContext<PlatformAuthState | null>(null);

/**
 * Server-resolved auth capability (Auth.js Keycloak env).
 * Avoids a client waterfall of /healthz + /api/auth/providers on every mount.
 */
export function PlatformAuthProvider({
  keycloakConfigured,
  children,
}: {
  keycloakConfigured: boolean;
  children: React.ReactNode;
}) {
  return (
    <PlatformAuthContext
      value={{
        keycloakConfigured,
        oidcEnabled: keycloakConfigured,
        loading: false,
      }}
    >
      {children}
    </PlatformAuthContext>
  );
}

export function usePlatformAuthContext(): PlatformAuthState | null {
  return use(PlatformAuthContext);
}
