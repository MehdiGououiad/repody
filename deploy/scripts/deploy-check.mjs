#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const steps = [
  ["helm-deps", "node", ["scripts/helm-deps.mjs"]],
];

steps.push(["node-check-k8s-local", "node", ["--check", "deploy/scripts/k8s-local.mjs"]]);
steps.push(["node-check-k8s-local-smoke", "node", ["--check", "deploy/scripts/k8s-local-smoke.mjs"]]);
steps.push(["check-k8s-local", "node", ["deploy/scripts/check-k8s-local.mjs"]]);
steps.push(["helm-lint-repody", "helm", ["lint", "deploy/helm/repody"]]);
steps.push([
  "helm-template-staging",
  "helm",
  [
    "template",
    "repody",
    "deploy/helm/repody",
    "-f",
    "deploy/helm/repody/values.yaml",
    "-f",
    "deploy/helm/repody/values-staging.yaml",
  ],
]);
steps.push([
  "helm-template-production-managed",
  "helm",
  [
    "template",
    "repody",
    "deploy/helm/repody",
    "-f",
    "deploy/helm/repody/values-production.yaml.example",
    "-f",
    "deploy/helm/repody/values-production.onprem-managed.yaml.example",
    "-f",
    "deploy/helm/repody/values-production.gateway.yaml.example",
  ],
]);
steps.push([
  "enterprise-secrets-contract",
  "node",
  ["deploy/scripts/check-enterprise-secrets.mjs", "--allow-placeholders"],
]);
steps.push([
  "kustomize-cnpg-data-plane",
  "kubectl",
  ["kustomize", "deploy/managed/cloudnativepg"],
]);
steps.push([
  "k8s-local-addons-gitops-dry-run",
  "kubectl",
  ["apply", "--dry-run=client", "-f", "deploy/k8s/local-addons-gitops.yaml"],
]);
steps.push([
  "k8s-local-addons-obs-dry-run",
  "kubectl",
  ["apply", "--dry-run=client", "-f", "deploy/k8s/local-addons-obs.yaml"],
]);

let failed = false;
for (const [label, cmd, args] of steps) {
  console.error(`\n▶ ${label}\n`);
  if (spawnSync(cmd, args, { stdio: "inherit" }).status !== 0) {
    failed = true;
    console.error(`\n✗ ${label} failed\n`);
  }
}

process.exit(failed ? 1 : 0);
