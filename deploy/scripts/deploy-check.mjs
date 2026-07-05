#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const verbose = /^(1|true|yes)$/i.test(process.env.REPODY_DEPLOY_CHECK_VERBOSE ?? "");

const steps = [
  ["helm-deps", "node", ["scripts/helm-deps.mjs", "--check"]],
  ["toolchain", "node", ["scripts/check-toolchain.mjs"]],
  ["node-check-build-images", "node", ["--check", "deploy/scripts/build-images.mjs"]],
  ["node-check-openshift-client-test", "node", ["--check", "deploy/scripts/openshift-client-test.mjs"]],
  ["node-check-runtime-env", "node", ["--check", "deploy/scripts/runtime-env.mjs"]],
  ["node-check-local-dev", "node", ["--check", "deploy/scripts/local-dev.mjs"]],
  ["node-check-client-integration", "node", ["--check", "deploy/scripts/client-integration-check.mjs"]],
  ["node-check-prod-readiness", "node", ["--check", "deploy/scripts/prod-readiness-check.mjs"]],
  ["node-check-ocr-soak", "node", ["--check", "deploy/scripts/ocr-soak.mjs"]],
  ["node-check-package-scripts", "node", ["--check", "deploy/scripts/check-package-scripts.mjs"]],
  ["node-check-command-docs", "node", ["--check", "deploy/scripts/check-command-docs.mjs"]],
  ["node-check-architecture", "node", ["--check", "deploy/scripts/check-architecture.mjs"]],
  ["node-check-release-supply-chain", "node", ["--check", "deploy/scripts/release-supply-chain.mjs"]],
  ["node-check-security-scan", "node", ["--check", "deploy/scripts/security-scan.mjs"]],
  ["release-supply-chain-check", "node", ["deploy/scripts/release-supply-chain.mjs", "--check"]],
  ["node-check-run-worker", "node", ["--check", "deploy/scripts/run-worker.mjs"]],
  ["node-check-deploy-staging", "node", ["--check", "deploy/scripts/deploy-staging.mjs"]],
  ["node-check-run-platform-e2e", "node", ["--check", "scripts/run-platform-e2e.mjs"]],
  ["package-scripts", "node", ["deploy/scripts/check-package-scripts.mjs"]],
  ["command-docs", "node", ["deploy/scripts/check-command-docs.mjs"]],
  ["architecture", "node", ["deploy/scripts/check-architecture.mjs"]],
  ["release-scripts", "node", ["deploy/scripts/check-release-scripts.mjs"]],
  ["helm-lint-repody", "helm", ["lint", "deploy/helm/repody"]],
  ["helm-lint-repody-data", "helm", ["lint", "deploy/helm/repody-data"]],
  ["helm-lint-repody-auth", "helm", ["lint", "deploy/helm/repody-auth"]],
  [
    "helm-template-staging",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      "deploy/helm/repody/values-common.yaml",
      "-f",
      "deploy/helm/repody/values-staging.yaml",
    ],
  ],
  [
    "helm-template-production-managed",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      "deploy/helm/repody/values-common.yaml",
      "-f",
      "deploy/helm/repody/values-production.yaml.example",
      "-f",
      "deploy/helm/repody/values-production.onprem-managed.yaml.example",
      "-f",
      "deploy/helm/repody/values-production.gateway.yaml.example",
    ],
  ],
  [
    "helm-template-client-bundled",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      "deploy/helm/repody/values-common.yaml",
      "-f",
      "deploy/client/values-bundled.example.yaml",
      "-f",
      "deploy/client/values-enterprise.example.yaml",
    ],
  ],
  [
    "helm-template-client-external",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      "deploy/helm/repody/values-common.yaml",
      "-f",
      "deploy/client/values-external.example.yaml",
      "-f",
      "deploy/client/values-enterprise.example.yaml",
    ],
  ],
  [
    "helm-template-openshift",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      "deploy/helm/repody/values-common.yaml",
      "-f",
      "deploy/client/values-external.example.yaml",
      "-f",
      "deploy/client/values-enterprise.example.yaml",
      "-f",
      "deploy/values/openshift.yaml",
      "--set",
      "ingress.host=app.example.com",
      "--set",
      "ingress.apiHost=api.example.com",
      "--set",
      "ingress.filesHost=files.example.com",
    ],
  ],
  [
    "enterprise-secrets-contract",
    "node",
    ["deploy/scripts/check-enterprise-secrets.mjs", "--allow-placeholders"],
  ],
  ["kustomize-cnpg-data-plane", "kubectl", ["kustomize", "deploy/managed/cloudnativepg"]],
  ["client-manifests", "node", ["deploy/scripts/check-client-manifests.mjs"]],
];

let failed = false;
for (const [label, cmd, args] of steps) {
  console.error(`\n> ${label}`);
  const result = spawnSync(cmd, args, {
    encoding: "utf8",
    maxBuffer: 50 * 1024 * 1024,
  });
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  if (verbose && output.trim()) {
    console.error(output.trimEnd());
  }
  if (result.status !== 0) {
    failed = true;
    if (!verbose && output.trim()) {
      console.error(output.trimEnd());
    }
    console.error(`failed: ${label}`);
  } else {
    console.error(`ok: ${label}`);
  }
}

process.exit(failed ? 1 : 0);
