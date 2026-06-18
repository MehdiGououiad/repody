#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const steps = [
  ["sync-stacks", "node", ["deploy/scripts/sync-deploy-stacks.mjs", "--check"]],
  ["validate-compose", "node", ["deploy/scripts/validate-compose-stacks.mjs"]],
  ["verify-helm-parity", "node", ["deploy/scripts/verify-helm-compose-parity.mjs"]],
];

steps.push(["helm-lint-repody", "helm", ["lint", "deploy/helm/repody"]]);
steps.push(["helm-lint-inference-llamacpp", "helm", ["lint", "deploy/helm/inference-llamacpp"]]);
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
    "--set",
    "secrets.create=true",
    "--set",
    "secrets.authSecret=staging-check-auth-secret-32chars!",
    "--set",
    "secrets.keycloakClientSecret=staging-check-kc-secret",
    "--set",
    "keycloak.adminPassword=staging-check-admin",
    "--set",
    "postgresql.auth.password=staging-pg",
    "--set",
    "minio.auth.rootPassword=staging-minio",
    "--set",
    "hatchet.postgresPassword=staging-hatchet",
  ],
]);

if (process.platform !== "win32") {
  steps.push(["validate-vps", "bash", ["deploy/cloud/validate.sh"]]);
}

let failed = false;
for (const [label, cmd, args] of steps) {
  console.error(`\n▶ ${label}\n`);
  if (spawnSync(cmd, args, { stdio: "inherit" }).status !== 0) {
    failed = true;
    console.error(`\n✗ ${label} failed\n`);
  }
}

process.exit(failed ? 1 : 0);
