#!/usr/bin/env node
/**
 * Client integration preflight - run what an integrator runs before go-live.
 *
 *   pnpm client:check
 *   pnpm client:check -- --live   # also smoke + Playwright when cluster is up
 */
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { commandFor } from "./runtime-env.mjs";

const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const live = process.argv.includes("--live");

const clientExternalValues = "deploy/client/values-external.example.yaml";
const clientBundledValues = "deploy/client/values-bundled.example.yaml";
const clientEnterpriseValues = "deploy/client/values-enterprise.example.yaml";
const clientValues = clientExternalValues;
const chartCommonValues = "deploy/helm/repody/values-common.yaml";
const clientRuntimeEs = "deploy/client/secrets/runtime.externalsecret.example.yaml";

function run(label, cmd, args, { optional = false, quiet = false, shell = false } = {}) {
  console.error(`\n> ${label}\n`);
  const result = spawnSync(commandFor(cmd), args, {
    stdio: quiet ? "pipe" : "inherit",
    cwd: root,
    shell,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    if (optional) {
      console.error(`warn: ${label} skipped or failed (optional)\n`);
      return false;
    }
    console.error(`\nerror: ${label} failed\n`);
    process.exit(result.status ?? 1);
  }
  return true;
}

function curlOk(url) {
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const result = spawnSync(curl, ["-fsS", "--max-time", "8", url], {
    encoding: "utf8",
    cwd: root,
    shell: false,
  });
  return result.status === 0 ? result.stdout.trim() : null;
}

const steps = [
  [
    "Helm production render (external + enterprise)",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      chartCommonValues,
      "-f",
      clientExternalValues,
      "-f",
      clientEnterpriseValues,
    ],
    { quiet: true },
  ],
  [
    "Helm production render (bundled + enterprise)",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      chartCommonValues,
      "-f",
      clientBundledValues,
      "-f",
      clientEnterpriseValues,
    ],
    { quiet: true },
  ],
  [
    "Helm OpenShift render (bundled + enterprise)",
    "helm",
    [
      "template",
      "repody",
      "deploy/helm/repody",
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      chartCommonValues,
      "-f",
      clientBundledValues,
      "-f",
      clientEnterpriseValues,
      "-f",
      "deploy/values/openshift.yaml",
      "--set",
      "ingress.host=app.example.com",
      "--set",
      "ingress.apiHost=api.example.com",
      "--set",
      "ingress.filesHost=files.example.com",
    ],
    { quiet: true },
  ],
  [
    "Enterprise secret contract",
    "node",
    [
      "deploy/scripts/check-enterprise-secrets.mjs",
      "--allow-placeholders",
      "--values",
      chartCommonValues,
      "--values",
      clientExternalValues,
      "--values",
      clientEnterpriseValues,
      "--external-secret",
      clientRuntimeEs,
    ],
  ],
  [
    "Client manifest contract",
    "node",
    ["deploy/scripts/check-client-manifests.mjs"],
  ],
];

console.error("Client integration preflight\n");

for (const entry of steps) {
  const [label, cmd, args, opts = {}] = entry;
  run(label, cmd, args, opts);
}

const registry = process.env.REPODY_IMAGE_REGISTRY ?? "harbor.example.com/repody";
console.error(`\ninfo: set REPODY_IMAGE_REGISTRY for release pushes (current: ${registry})\n`);

const apiPort = process.env.REPODY_API_PORT || "8000";
const apiLive =
  curlOk(`http://localhost:${apiPort}/v1/healthz/live`) ||
  curlOk("http://api.repody.local/v1/healthz/live");
if (apiLive) {
  console.error(`ok: API live probe: ${apiLive}\n`);
} else {
  console.error("warn: API not reachable — start Compose dev (docs/deploy/LOCAL.md) or K8s stack\n");
}

if (live && apiLive) {
  run("Playwright UI smoke", "pnpm", ["test:e2e:smoke"], { optional: false });
} else if (live) {
  console.error("warn: --live skipped Playwright (API not up)\n");
}

console.error(`
Client integration preflight passed.

Client guide: docs/deploy/CLIENT.md

Next steps for the client:
  1. Copy deploy/client/values-external.example.yaml (or values-bundled.example.yaml) -> private GitOps repo (values.yaml)
  2. Apply ExternalSecrets in namespace repody (registry-pull + runtime)
  3. Helm: helm upgrade --install repody deploy/helm/repody -n repody -f values.yaml
     Argo CD: kubectl apply -f deploy/client/argocd.application.yaml
  4. Verify: curl https://api.<client-domain>/v1/healthz/live

Vendor release images:
  REPODY_IMAGE_REGISTRY=harbor.vendor.example.com/repody pnpm images:release
`);
