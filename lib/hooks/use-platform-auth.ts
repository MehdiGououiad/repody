"use client";

import { useEffect, useState } from "react";

export type PlatformAuthState = {
  /** Keycloak sign-in is available (API OIDC on + Auth.js provider configured). */
  oidcEnabled: boolean;
  /** Auth.js has a Keycloak provider (env vars present) but API/Keycloak may be off. */
  keycloakConfigured: boolean;
  loading: boolean;
};

export function usePlatformAuth(): PlatformAuthState {
  const [state, setState] = useState<{
    oidcEnabled: boolean;
    keycloakConfigured: boolean;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [healthRes, providersRes] = await Promise.all([
          fetch("/api/v1/healthz", { cache: "no-store" }),
          fetch("/api/auth/providers", { cache: "no-store" }),
        ]);

        const apiOidc =
          healthRes.ok &&
          Boolean(
            ((await healthRes.json()) as { oidcEnabled?: boolean }).oidcEnabled
          );
        const providers = providersRes.ok
          ? ((await providersRes.json()) as Record<string, unknown>)
          : {};
        const keycloakConfigured = Boolean(providers.keycloak);

        if (!cancelled) {
          setState({
            keycloakConfigured,
            oidcEnabled: keycloakConfigured && apiOidc,
          });
        }
      } catch {
        if (!cancelled) {
          setState({ keycloakConfigured: false, oidcEnabled: false });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    oidcEnabled: state?.oidcEnabled ?? false,
    keycloakConfigured: state?.keycloakConfigured ?? false,
    loading: state === null,
  };
}
