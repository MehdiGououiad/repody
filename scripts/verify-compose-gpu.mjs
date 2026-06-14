#!/usr/bin/env node
/**
 * Validate merged GPU compose without needing a GPU.
 * Checks service graph + critical Repody VLM env vars.
 */
import { spawnSync } from "node:child_process";

const GPU_FILES = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.gpu.yaml",
  "-f",
  "compose.prod.yaml",
];

const VALIDATE_ENV = {
  ...process.env,
  VLLM_SERVED_MODEL: process.env.VLLM_SERVED_MODEL ?? "numind/NuExtract3",
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

const serviceList = services.stdout
  .trim()
  .split(/\r?\n/)
  .map((line) => line.trim())
  .filter(Boolean);

const requiredServices = ["api", "worker", "worker-fast", "web", "vllm"];
const missingServices = requiredServices.filter((name) => !serviceList.includes(name));
if (missingServices.length) {
  console.error(`GPU compose missing services: ${missingServices.join(", ")}`);
  process.exit(1);
}

const config = run(["config"]);
if (config.status !== 0) {
  console.error(config.stderr || config.stdout);
  process.exit(config.status ?? 1);
}

const merged = config.stdout;
const requiredTokens = [
  "AUDIT_INFERENCE_MODE",
  "AUDIT_VLLM_BASE_URL",
  "AUDIT_VLLM_SERVED_MODEL",
  "AUDIT_DOCKER_MODEL_RUNNER_BASE_URL",
  "AUDIT_REPODY_VLM_ENABLED",
  "AUDIT_DEFAULT_OCR_MODEL",
  "numind/NuExtract3",
  "speculative-config",
  "qwen3_next_mtp",
];

const missingTokens = requiredTokens.filter((token) => !merged.includes(token));
if (missingTokens.length) {
  console.error(`GPU compose missing config: ${missingTokens.join(", ")}`);
  process.exit(1);
}

if (!merged.includes("AUDIT_INFERENCE_MODE: vllm") && !merged.includes('AUDIT_INFERENCE_MODE: "vllm"')) {
  console.error("GPU compose must set AUDIT_INFERENCE_MODE to vllm");
  process.exit(1);
}

console.log("GPU compose stack validates OK (no GPU required for this check).");
console.log(`Services: ${serviceList.join(", ")}`);
console.log("Deploy with: pnpm docker:deploy:gpu");
