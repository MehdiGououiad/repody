/** Shared TanStack Query keys for browser data hooks. */
export const queryKeys = {
  platformConfig: ["platform", "config"] as const,
  backendHealth: ["backend", "health"] as const,
  dashboard: {
    live: ["dashboard", "live"] as const,
  },
  checkRules: (draftFingerprint: string) => ["check-rules", draftFingerprint] as const,
} as const;
