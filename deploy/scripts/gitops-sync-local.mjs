#!/usr/bin/env node
/**
 * Sync local Repody Argo CD apps from Git (refresh + wait; no argocd CLI in-cluster).
 */
import { fileURLToPath } from "node:url";
import path from "node:path";
import { gitHeadRevision } from "./git-sha.mjs";
import { createProcessAdapter } from "./k8s-local-process.mjs";
import {
  createGitOpsCommands,
  LOCAL_ARGO_APP_NAMES,
} from "./k8s-local-gitops.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ARGO_NS = "argocd";

const { captureOptional, run } = createProcessAdapter(root);
const {
  refreshArgoApplications,
  waitForArgoApplicationsSynced,
} = createGitOpsCommands({ captureOptional, argoNamespace: ARGO_NS });

const revision = process.env.REPODY_GITOPS_REVISION ?? gitHeadRevision(root);

console.error(`> Argo CD sync local stack @ ${revision.slice(0, 12)}\n`);

for (const app of LOCAL_ARGO_APP_NAMES) {
  console.error(`> refresh ${app}`);
}
refreshArgoApplications();

console.error("> waiting for Argo CD applications to report Synced");
await waitForArgoApplicationsSynced(600_000);

if (!process.env.REPODY_SKIP_PLATFORM_SECRET_SYNC) {
  run("node", ["deploy/scripts/sync-platform-secrets.mjs"]);
  const namespace = process.env.REPODY_APP_NAMESPACE ?? "repody-app";
  const deployments = captureOptional("kubectl", [
    "-n",
    namespace,
    "get",
    "deploy",
    "-l",
    "app.kubernetes.io/instance=repody",
    "-o",
    "name",
  ]);
  if (deployments) {
    run("kubectl", [
      "-n",
      namespace,
      "rollout",
      "restart",
      "deploy",
      "-l",
      "app.kubernetes.io/instance=repody",
    ]);
  }
}

const phases = LOCAL_ARGO_APP_NAMES.map((app) => {
  const phase = captureOptional("kubectl", [
    "-n",
    ARGO_NS,
    "get",
    `applications.argoproj.io/${app}`,
    "-o",
    "jsonpath={.status.sync.status},{.status.health.status}",
  ]);
  const [sync, health] = (phase ?? "Unknown,Unknown").split(",");
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
