#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  REPODY_VLM_DEFAULT_TARGET,
  REPODY_VLM_PACKAGE_FROM,
  REPODY_VLM_PULL_SOURCE,
} from "../deploy/repody-vlm-model.constants.mjs";

const target = process.env.AUDIT_REPODY_VLM_MODEL ?? REPODY_VLM_DEFAULT_TARGET;
const shellScript = join(
  dirname(fileURLToPath(import.meta.url)),
  "model-pull-repody-vlm.sh"
);

function runDockerModel(args) {
  console.error(`-> docker ${args.join(" ")}`);
  const result = spawnSync("docker", args, { stdio: "inherit" });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

if (process.platform !== "win32") {
  const bash = spawnSync("bash", [shellScript], {
    stdio: "inherit",
    env: { ...process.env, AUDIT_REPODY_VLM_MODEL: target },
  });
  process.exit(bash.status ?? 1);
}

const inspect = spawnSync("docker", ["model", "inspect", target], {
  stdio: "ignore",
});
if (inspect.status === 0) {
  console.error(`Repody VLM model ready: ${target}`);
  process.exit(0);
}

runDockerModel(["model", "pull", REPODY_VLM_PULL_SOURCE]);
runDockerModel([
  "model",
  "package",
  "--from",
  REPODY_VLM_PACKAGE_FROM,
  "--context-size",
  "16384",
  target,
]);
