#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { stackFileArgs } from "../deploy/platform-modules.mjs";

const [profile = "full", ...rawExtra] = process.argv.slice(2);
const extra = rawExtra[0] === "--" ? rawExtra.slice(1) : rawExtra;
const compose = ["compose", ...stackFileArgs("dev")];

const commands = {
  quick: [
    ...compose,
    "run",
    "--rm",
    "--no-deps",
    "-v",
    "./e2e:/app/e2e:ro",
    "-v",
    "./benchmark-reports:/app/benchmark-reports",
    "api",
    "python",
    "scripts/benchmark_suite.py",
    "--profile",
    "quick",
  ],
  models: [
    ...compose,
    "run",
    "--rm",
    "--no-deps",
    "-v",
    "./e2e:/app/e2e:ro",
    "-v",
    "./benchmark-reports:/app/benchmark-reports",
    "api",
    "python",
    "scripts/benchmark_suite.py",
    "--profile",
    "models",
  ],
  full: [
    ...compose,
    "run",
    "--rm",
    "--no-deps",
    "-v",
    "./e2e:/app/e2e:ro",
    "-v",
    "./benchmark-reports:/app/benchmark-reports",
    "api",
    "python",
    "scripts/benchmark_suite.py",
    "--profile",
    "full",
  ],
  "document-models": [
    ...compose,
    "run",
    "--rm",
    "--no-deps",
    "-v",
    "./e2e:/app/e2e:ro",
    "api",
    "python",
    "scripts/benchmark_document_models.py",
    "/app/e2e/fixtures/documents/Facture.pdf",
  ],
};

const args = commands[profile];
if (!args) {
  console.error(`Unknown benchmark profile: ${profile}`);
  console.error(`Available: ${Object.keys(commands).join(", ")}`);
  process.exit(1);
}

const result = spawnSync("docker", [...args, ...extra], {
  stdio: "inherit",
  shell: process.platform === "win32",
});
process.exit(result.status ?? 1);
