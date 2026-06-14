#!/usr/bin/env node

import { spawnSync } from "node:child_process";

// Upstream public GGUF weights — Repody VLM is the local Docker Model Runner tag only.
const pullSource = "hf.co/numind/NuExtract3-GGUF:Q4_K_M";
const packageFrom = "huggingface.co/numind/nuextract3-gguf:Q4_K_M";
const target =
  process.env.AUDIT_REPODY_VLM_MODEL ?? "agentcontrol/repody-vlm:q4_k_m-16k";

function run(args) {
  console.error(`-> docker ${args.join(" ")}`);
  const result = spawnSync("docker", args, {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run(["model", "pull", pullSource]);
run([
  "model",
  "package",
  "--from",
  packageFrom,
  "--context-size",
  "16384",
  target,
]);
