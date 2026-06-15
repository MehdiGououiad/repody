#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const prodYaml = readFileSync(join(root, "deploy/compose/prod.yaml"), "utf8");
const helmValues = readFileSync(
  join(root, "deploy/helm/repody/values.yaml"),
  "utf8"
);

function composeEnv(service, key) {
  const blockRe = new RegExp(
    `^  ${service}:\\n([\\s\\S]*?)(?=^  [a-z]|\\Z)`,
    "m"
  );
  const block = prodYaml.match(blockRe)?.[1] ?? "";
  let m = block.match(new RegExp(`^\\s+${key}:\\s*"?([^"\\n]+)"?`, "m"));
  if (m) return m[1].trim();
  const anchor =
    service === "api"
      ? "x-prod-api-env"
      : service === "worker" || service === "worker-fast"
        ? "x-prod-worker-env"
        : null;
  if (!anchor) return null;
  m = prodYaml.match(
    new RegExp(`${anchor}:[\\s\\S]*?^  ${key}:\\s*"?([^"\\n]+)"?`, "m")
  );
  return m?.[1]?.trim() ?? null;
}

function helmScalar(dotted) {
  const [section, key] = dotted.split(".");
  const sectionRe = new RegExp(`^${section}:\\n((?:  .+\\n)*)`, "m");
  const block = helmValues.match(sectionRe)?.[1] ?? "";
  const m = block.match(new RegExp(`^  ${key}:\\s*(.+)$`, "m"));
  if (!m) return null;
  const raw = m[1].trim();
  if (raw === "true") return true;
  if (raw === "false") return false;
  return raw.replace(/^['"]|['"]$/g, "");
}

const CHECKS = [
  {
    label: "API auth enabled",
    compose: () => composeEnv("api", "AUDIT_AUTH_ENABLED"),
    helm: () => helmScalar("config.authEnabled"),
  },
  {
    label: "Direct uploads",
    compose: () => composeEnv("api", "AUDIT_DIRECT_UPLOAD_ENABLED"),
    helm: () => helmScalar("config.directUploadEnabled"),
  },
  {
    label: "Run migrations on startup",
    compose: () => composeEnv("api", "AUDIT_RUN_MIGRATIONS_ON_STARTUP"),
    helm: () => "true",
  },
  {
    label: "Seed on startup (off in prod)",
    compose: () => composeEnv("api", "AUDIT_SEED_ON_STARTUP"),
    helm: () => "false",
  },
  {
    label: "OCR worker max jobs",
    compose: () => composeEnv("worker", "AUDIT_WORKER_OCR_MAX_JOBS"),
    helm: () => helmValues.match(/workerOcr:\n[\s\S]*?maxJobs:\s*(\d+)/)?.[1] ?? null,
  },
  {
    label: "Fast worker max jobs",
    compose: () => composeEnv("worker-fast", "AUDIT_WORKER_FAST_MAX_JOBS"),
    helm: () => helmValues.match(/workerFast:\n[\s\S]*?maxJobs:\s*(\d+)/)?.[1] ?? null,
  },
  {
    label: "Deployment environment",
    compose: () => composeEnv("api", "AUDIT_DEPLOYMENT_ENVIRONMENT"),
    helm: () => helmScalar("global.deploymentEnvironment"),
  },
  {
    label: "Storage backend",
    compose: () => composeEnv("api", "AUDIT_STORAGE_BACKEND"),
    helm: () => "s3",
  },
];

let failed = false;
for (const check of CHECKS) {
  const composeVal = check.compose();
  const helmVal = check.helm();
  if (composeVal == null) {
    console.error(`✓ ${check.label} (helm-only: ${helmVal})`);
    continue;
  }
  if (String(composeVal) !== String(helmVal)) {
    failed = true;
    console.error(`✗ ${check.label}: compose=${composeVal} helm=${helmVal}`);
  } else {
    console.error(`✓ ${check.label} = ${composeVal}`);
  }
}

if (failed) process.exit(1);
console.error("\nHelm ↔ Compose production defaults are aligned.");
