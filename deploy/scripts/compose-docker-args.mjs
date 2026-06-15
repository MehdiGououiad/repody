/**
 * Docker compose file/profile args aligned with deploy/scripts/compose.mjs resolveSpec().
 */
import { existsSync } from "node:fs";
import { join } from "node:path";
import { COMPOSE } from "../compose-paths.mjs";
import { HATCHET_INIT_PROFILE, stackFiles } from "../platform-modules.mjs";

const PROJECT_ROOT = process.cwd();

/** Load repo-root `.env` (compose files live under deploy/compose/). */
export function dockerComposeRootArgs() {
  const envFile = join(PROJECT_ROOT, ".env");
  return existsSync(envFile) ? ["--env-file", envFile] : [];
}

/** @param {string} stack @param {import("../platform-modules.mjs").StackOverlays} [overlays] */
export function dockerComposeInvocation(stack, overlays = {}) {
  const paths = stackFiles(stack, overlays);
  const profiles = [HATCHET_INIT_PROFILE];
  const obsMode = process.env.AUDIT_DEV_OBS ?? "none";

  if (stack === "dev" && obsMode !== "none") {
    if (!paths.includes(COMPOSE.observability)) {
      paths.push(COMPOSE.observability);
    }
    profiles.push("obs");
    if (obsMode === "traces") {
      if (!paths.includes(COMPOSE.observabilityTraces)) {
        paths.push(COMPOSE.observabilityTraces);
      }
      profiles.push("obs-traces");
    }
  }

  return {
    fileArgs: paths.flatMap((p) => ["-f", p]),
    profileArgs: [...new Set(profiles)].flatMap((p) => ["--profile", p]),
  };
}
