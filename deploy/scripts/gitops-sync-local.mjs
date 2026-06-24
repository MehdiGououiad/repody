#!/usr/bin/env node
/**
 * Sync local Repody Argo CD apps from Git (in-cluster Argo CD, no CLI login).
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { gitHeadRevision } from "./git-sha.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const APPS = [
  "repody-local-data",
  "repody-local-queue",
  "repody-local-auth",
  "repody-local-app",
];
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

console.error(`> Argo CD sync local stack @ ${revision.slice(0, 12)}\n`);

for (const app of APPS) {
  console.error(`> sync ${app}`);
  run("kubectl", [
    "-n",
    ARGO_NS,
    "exec",
    "deploy/argocd-server",
    "--",
    "argocd",
    "app",
    "sync",
    app,
    "--revision",
    revision,
    "--core",
    "--timeout",
    "600",
  ]);
}

if (!process.env.REPODY_SKIP_PLATFORM_SECRET_SYNC) {
  run("node", ["deploy/scripts/sync-platform-secrets.mjs"]);
  run("kubectl", [
    "-n",
    process.env.REPODY_APP_NAMESPACE ?? "repody-app",
    "rollout",
    "restart",
    "deploy",
    "-l",
    "app.kubernetes.io/instance=repody",
    "--ignore-not-found",
  ]);
}

const phases = APPS.map((app) => {
  const phase = capture("kubectl", [
    "-n",
    ARGO_NS,
    "get",
    `applications.argoproj.io/${app}`,
    "-o",
    "jsonpath={.status.sync.status},{.status.health.status}",
  ]);
  const [sync, health] = phase.split(",");
  return { app, sync, health };
});

console.error("\nArgo CD status:");
for (const { app, sync, health } of phases) {
  console.error(`  ${app}: sync=${sync} health=${health}`);
}

const notSynced = phases.filter((p) => p.sync !== "Synced");
if (notSynced.length) {
  console.error(
    "\nSome apps are not Synced — ensure values are pushed to the Application repo/branch.",
  );
  process.exit(1);
}
