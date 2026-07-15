#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { resolveExecutable } from "../deploy/scripts/runtime-env.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backend = resolve(root, "backend");
const rawArgs = process.argv.slice(2);

function usage() {
  console.error("Usage: node scripts/backend-run.mjs [--dev] <command> [...args]");
  process.exit(2);
}

const uvArgs = ["run"];
const commandArgs = [];
for (const arg of rawArgs) {
  if (arg === "--dev") {
    uvArgs.push("--extra", "dev", "--extra", "otel");
  } else {
    commandArgs.push(arg);
  }
}

if (!commandArgs.length) usage();

const result = spawnSync(resolveExecutable("uv"), [...uvArgs, ...commandArgs], {
  cwd: backend,
  stdio: "inherit",
  shell: false,
});

process.exit(result.status ?? 1);
