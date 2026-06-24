#!/usr/bin/env node
/**
 * Primary dev inner loop: Skaffold file sync into running pods (see skaffold.yaml).
 * Run once after bootstrap: pnpm dev  →  pnpm dev:sync
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { resolveLocalRegistryConfig } from "./k8s-local-registry-config.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const REGISTRY_CONFIG = resolveLocalRegistryConfig(root);
const LOCAL_REGISTRY = REGISTRY_CONFIG.localRegistry;
const CLUSTER = process.env.REPODY_KIND_CLUSTER ?? "repody-local";
const NS = "repody";

function run(cmd, args) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    cwd: root,
    shell: process.platform === "win32",
    env: process.env,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function clusterReady() {
  const ctx = spawnSync(
    "kubectl",
    ["config", "use-context", `kind-${CLUSTER}`],
    { encoding: "utf8", shell: process.platform === "win32" },
  );
  if (ctx.status !== 0) return false;
  const release = spawnSync(
    "helm",
    ["status", "repody", "-n", NS],
    { encoding: "utf8", shell: process.platform === "win32" },
  );
  return release.status === 0;
}

const check = spawnSync("skaffold", ["version"], {
  encoding: "utf8",
  shell: process.platform === "win32",
});
if (check.status !== 0) {
  console.error(
    "Skaffold is required for pnpm dev:sync. Install: https://skaffold.dev/docs/install/",
  );
  process.exit(1);
}

if (!clusterReady()) {
  console.error(
    "Cluster or repody release not found. Bootstrap once, then use this as your daily loop:\n",
  );
  console.error("  pnpm dev          # Helm deploy (first time or after pnpm stop)");
  console.error("  pnpm dev:sync     # Skaffold hot sync (daily code changes)\n");
  process.exit(1);
}

console.error(
  `Skaffold dev (default-repo=${LOCAL_REGISTRY}, context=kind-${CLUSTER})`,
);
console.error("Python → API pod with uvicorn --reload. Web/backend image rebuilds only when Skaffold detects changes.");
console.error("Ctrl+C to stop Skaffold (cluster keeps running).\n");

run("skaffold", [
  "dev",
  "--default-repo",
  LOCAL_REGISTRY,
  "--kube-context",
  `kind-${CLUSTER}`,
  "--port-forward=false",
]);
