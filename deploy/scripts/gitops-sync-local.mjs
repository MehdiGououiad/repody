#!/usr/bin/env node
/**
 * Sync repody-local from Git (in-cluster Argo CD, no CLI login).
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { gitHeadRevision } from "./git-sha.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const APP = "repody-local";
const ARGO_NS = "argocd";

function run(cmd, args) {
  const result = spawnSync(cmd, args, {
    cwd: root,
    encoding: "utf8",
    shell: false,
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function capture(cmd, args) {
  const result = spawnSync(cmd, args, {
    cwd: root,
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} failed`);
  }
  return result.stdout.trim();
}

const revision = process.env.REPODY_GITOPS_REVISION ?? gitHeadRevision(root);

console.error(`> Argo CD sync ${APP} @ ${revision.slice(0, 12)}\n`);

run("kubectl", [
  "-n",
  ARGO_NS,
  "exec",
  "deploy/argocd-server",
  "--",
  "argocd",
  "app",
  "sync",
  APP,
  "--revision",
  revision,
  "--core",
  "--timeout",
  "600",
]);

const phase = capture("kubectl", [
  "-n",
  ARGO_NS,
  "get",
  `applications.argoproj.io/${APP}`,
  "-o",
  "jsonpath={.status.sync.status},{.status.health.status},{.status.sync.revision}",
]);
const [sync, health, syncedRev] = phase.split(",");
console.error(`\nok: sync=${sync} health=${health} revision=${syncedRev?.slice(0, 12) ?? "?"}`);

if (sync !== "Synced") {
  console.error(
    "Argo CD is not Synced — ensure values-local-images.yaml is pushed to the Application repo/branch.",
  );
  process.exit(1);
}
