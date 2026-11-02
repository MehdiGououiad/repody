#!/usr/bin/env node
import { spawn } from "node:child_process";
import { ROOT, uvBackend } from "./runtime-env.mjs";

const pool = process.argv[2] || "extract";
if (!["extract", "fast"].includes(pool)) {
  console.error("Usage: node deploy/scripts/run-worker.mjs extract|fast");
  process.exit(1);
}

const child = spawn(...uvBackend(["python", "-m", "repody.taskiq.worker"]), {
  cwd: ROOT,
  env: { ...process.env, AUDIT_WORKER_POOL: pool },
  stdio: "inherit",
});

child.on("exit", (code) => process.exit(code ?? 1));
