/** Shared Docker Compose file sets (keep in sync with scripts/docker.mjs). */

export const DEV_NOWARMUP = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.dev.yaml",
];

export const DEV_WARMUP = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.warmup.yaml",
];

export const PROD_CPU = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.prod.yaml",
];

export const PROD_CPU_WARMUP = [...PROD_CPU, "-f", "compose.warmup.yaml"];

/** @param {"dev" | "dev-warmup" | "prod" | "prod-warmup"} stack */
export function composeFilesForStack(stack) {
  switch (stack) {
    case "dev":
      return DEV_NOWARMUP;
    case "dev-warmup":
      return DEV_WARMUP;
    case "prod":
      return PROD_CPU;
    case "prod-warmup":
      return PROD_CPU_WARMUP;
    default:
      return DEV_WARMUP;
  }
}
