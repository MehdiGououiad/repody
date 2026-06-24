#!/usr/bin/env node
/**
 * Wipe local platform: kind cluster, Harbor runtime, and dev data dirs.
 *
 *   pnpm platform:reset              full wipe (default)
 *   pnpm platform:reset -- --keep-harbor   keep Harbor running + .runtime
 *   pnpm platform:reset -- --up      wipe then pnpm dev --minimal --reset
 */
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const argv = process.argv.slice(2);
const doUp = argv.includes("--up");
const keepHarbor = argv.includes("--keep-harbor");

function emptyDir(dir) {
  if (!existsSync(dir)) return;
  for (const name of readdirSync(dir)) {
    rmSync(path.join(dir, name), { recursive: true, force: true });
  }
}

function rmPath(target) {
  if (existsSync(target)) rmSync(target, { recursive: true, force: true });
}

function runNode(script, args = []) {
  const result = spawnSync("node", [script, ...args], {
    stdio: "inherit",
    cwd: root,
    shell: false,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.error("→ Tearing down local Kubernetes cluster…");
runNode("deploy/scripts/k8s-local.mjs", ["down", "--cluster"]);

if (!keepHarbor) {
  console.error("→ Stopping Harbor…");
  runNode("deploy/scripts/harbor-local.mjs", ["down"]);
  rmPath(path.join(root, "deploy/harbor/.runtime"));
  rmPath(path.join(root, "deploy/harbor/paths.harbor.local.env"));
}

console.error("→ Clearing local data directories…");
emptyDir(path.join(root, "benchmark-reports"));
emptyDir(path.join(root, "backend", "benchmark-reports-local"));
rmPath(path.join(root, "backend", ".data"));
emptyDir(path.join(root, "test-results"));
emptyDir(path.join(root, "playwright-report"));
emptyDir(path.join(root, "e2e", ".auth"));

console.log(
  keepHarbor
    ? "Platform data wiped (cluster removed; Harbor kept)."
    : "Platform wiped (cluster + Harbor runtime + local storage cleared).",
);

if (doUp) {
  console.error("→ pnpm dev -- --reset --minimal");
  const up = spawnSync(
    "node",
    ["deploy/scripts/k8s-local.mjs", "up", "--reset", "--minimal"],
    { stdio: "inherit", cwd: root, shell: false },
  );
  process.exit(up.status ?? 0);
}
