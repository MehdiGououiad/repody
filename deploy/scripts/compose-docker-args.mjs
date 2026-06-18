/**
 * Docker compose file/profile args aligned with deploy/scripts/compose.mjs resolveSpec().
 */
import { existsSync } from "node:fs";
import { join } from "node:path";
import { COMPOSE } from "../compose-paths.mjs";
import {
  buildPlatformSpec,
  parseModuleCsv,
} from "../platform-modules.mjs";

const PROJECT_ROOT = process.cwd();

/** Load repo-root `.env` (compose files live under deploy/compose/). */
export function dockerComposeRootArgs() {
  const envFile = join(PROJECT_ROOT, ".env");
  return existsSync(envFile) ? ["--env-file", envFile] : [];
}

/** @param {string} stack @param {import("../platform-modules.mjs").StackOverlays} [overlays] */
export function dockerComposeInvocation(stack, overlays = {}) {
  const withModules = parseModuleCsv(process.env.AUDIT_COMPOSE_WITH ?? "");
  let spec = buildPlatformSpec({
    stack,
    overlays,
    withModules,
  });

  const obsMode = process.env.AUDIT_DEV_OBS ?? "none";
  if (stack === "dev" && obsMode !== "none") {
    const filePaths = [...spec.filePaths];
    const profiles = [...spec.profiles];
    if (!filePaths.includes(COMPOSE.observability)) {
      filePaths.push(COMPOSE.observability);
    }
    if (!profiles.includes("obs")) {
      profiles.push("obs");
    }
    if (obsMode === "traces") {
      if (!filePaths.includes(COMPOSE.observabilityTraces)) {
        filePaths.push(COMPOSE.observabilityTraces);
      }
      if (!profiles.includes("obs-traces")) {
        profiles.push("obs-traces");
      }
    }
    spec = {
      ...spec,
      filePaths,
      fileArgs: filePaths.flatMap((p) => ["-f", p]),
      profiles,
    };
  }

  return {
    fileArgs: spec.fileArgs,
    profileArgs: [...new Set(spec.profiles)].flatMap((p) => ["--profile", p]),
  };
}
