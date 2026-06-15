#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { stackFileArgs } from "../platform-modules.mjs";

const GPU_FILES = stackFileArgs("gpu");

const VALIDATE_ENV = {
  ...process.env,
  VLLM_SERVED_MODEL: process.env.VLLM_SERVED_MODEL ?? "numind/NuExtract3",
  AUDIT_ADMIN_API_TOKEN: process.env.AUDIT_ADMIN_API_TOKEN ?? "ci-test-token",
  AUDIT_MINIO_PUBLIC_ENDPOINT:
    process.env.AUDIT_MINIO_PUBLIC_ENDPOINT ?? "files.example.com",
};

function run(args) {
  return spawnSync("docker", ["compose", ...GPU_FILES, ...args], {
    encoding: "utf-8",
    env: VALIDATE_ENV,
  });
}

const services = run(["config", "--services"]);
if (services.status !== 0) {
  console.error(services.stderr || services.stdout);
  process.exit(services.status ?? 1);
}

const serviceList = services.stdout.trim().split(/\r?\n/).filter(Boolean);
const required = ["api", "worker", "worker-fast", "web", "vllm"];
const missing = required.filter((n) => !serviceList.includes(n));
if (missing.length) {
  console.error(`GPU compose missing services: ${missing.join(", ")}`);
  process.exit(1);
}

const config = run(["config"]);
if (config.status !== 0) {
  console.error(config.stderr || config.stdout);
  process.exit(config.status ?? 1);
}

if (!config.stdout.includes("AUDIT_INFERENCE_MODE: vllm") &&
    !config.stdout.includes('AUDIT_INFERENCE_MODE: "vllm"')) {
  console.error("GPU compose must set AUDIT_INFERENCE_MODE to vllm");
  process.exit(1);
}

console.log("GPU compose validates OK.");
console.log("Deploy: pnpm compose up --stack=gpu --build");
