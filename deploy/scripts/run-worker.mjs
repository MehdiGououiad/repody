#!/usr/bin/env node
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pool = process.argv[2] || "extract";
if (!["extract", "fast"].includes(pool)) {
  console.error("Usage: node deploy/scripts/run-worker.mjs extract|fast");
  process.exit(1);
}

const child = spawn(
  process.execPath,
  ["scripts/backend-run.mjs", "python", "-m", "audit_workbench.taskiq.worker"],
  {
  cwd: ROOT,
  env: { ...process.env, AUDIT_WORKER_POOL: pool },
  stdio: "inherit",
  },
);

child.on("exit", (code) => process.exit(code ?? 1));
