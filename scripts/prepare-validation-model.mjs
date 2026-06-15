#!/usr/bin/env node

import { spawnSync } from "node:child_process";

const source = "hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M";
const normalizedSource = "huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M";
const target = "repody/validation:q4_k_m-4k";

function run(args) {
  console.error(`-> docker ${args.join(" ")}`);
  const result = spawnSync("docker", args, {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run(["model", "pull", source]);
run([
  "model",
  "package",
  "--from",
  normalizedSource,
  "--context-size",
  "4096",
  target,
]);
