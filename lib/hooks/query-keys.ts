/** Shared TanStack Query keys for browser data hooks. */
export const queryKeys = {
  catalog: {
    models: ["catalog", "models"] as const,
    rulesLibrary: ["catalog", "rules-library"] as const,
    platformConfig: ["catalog", "platform-config"] as const,
    modelRuntimeConfig: ["catalog", "model-runtime-config"] as const,
  },
  iam: {
    all: ["iam"] as const,
    me: () => ["iam", "me"] as const,
    catalog: () => ["iam", "catalog"] as const,
    users: (search = "") => ["iam", "users", search] as const,
  },
  backendHealth: ["backend", "health"] as const,
  dashboard: {
    live: ["dashboard", "live"] as const,
  },
  operator: {
    status: ["operator", "status"] as const,
    jobs: ["operator", "jobs"] as const,
    latestBenchmark: ["operator", "benchmarks", "latest"] as const,
    jobReport: (jobId: string) => ["operator", "jobs", jobId, "report"] as const,
  },
} as const;
