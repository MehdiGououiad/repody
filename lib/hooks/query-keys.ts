/** Shared TanStack Query keys for browser data hooks. */
export const queryKeys = {
  catalog: {
    models: ["catalog", "models"] as const,
    rulesLibrary: ["catalog", "rules-library"] as const,
    platformConfig: ["catalog", "platform-config"] as const,
  },
  backendHealth: ["backend", "health"] as const,
  dashboard: {
    live: ["dashboard", "live"] as const,
  },
} as const;
