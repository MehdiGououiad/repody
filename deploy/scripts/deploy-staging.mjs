#!/usr/bin/env node
/**
 * Deploy Repody staging stack to an existing Kubernetes cluster.
 *
 * Prerequisites:
 *   - kubectl context pointing at the target cluster
 *   - image pull secret in namespace repody, unless images are public
 *   - runtime secret when secrets.create=false
 *   - external OpenAI-compatible VLM endpoint
 *
 *   pnpm deploy:staging
 *   pnpm deploy:staging -- --argocd
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const NS = process.env.REPODY_NAMESPACE || "repody";
const REPODY_RELEASE = process.env.REPODY_HELM_RELEASE || "repody";
const IMAGE_TAG =
  process.env.REPODY_IMAGE_TAG ||
  (() => {
    const r = spawnSync("git", ["rev-parse", "--short=12", "HEAD"], {
      encoding: "utf8",
      cwd: root,
    });
    return r.status === 0 ? r.stdout.trim() : "latest";
  })();

const CHART_REPODY = path.join(root, "deploy/helm/repody");
const VALUES_STAGING = path.join(CHART_REPODY, "values-staging.yaml");
const ARGO_DIR = path.join(root, "deploy/argocd");

const useArgo = process.argv.includes("--argocd");

function run(cmd, args) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    cwd: root,
    shell: process.platform === "win32",
    env: process.env,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function heading(text) {
  console.error(`\n> ${text}\n`);
}

function helmImageSets() {
  const registry = process.env.REPODY_IMAGE_REGISTRY;
  const sets = [
    `images.backend.tag=${IMAGE_TAG}`,
    `images.api.tag=${IMAGE_TAG}`,
    `images.worker.tag=${IMAGE_TAG}`,
    `images.web.tag=${IMAGE_TAG}`,
  ];
  if (registry) {
    sets.push(
      `images.backend.repository=${registry}/repody-backend`,
      `images.api.repository=${registry}/repody-backend`,
      `images.worker.repository=${registry}/repody-backend`,
      `images.web.repository=${registry}/repody-web`,
    );
  }
  return sets.flatMap((s) => ["--set", s]);
}

function ensureNamespace() {
  run("kubectl", ["create", "namespace", NS, "--dry-run=client", "-o", "yaml"]);
  run("kubectl", ["create", "namespace", NS]);
}

function deployHelm() {
  heading("Helm dependencies");
  run("node", ["scripts/helm-deps.mjs"]);

  heading(`Installing Repody (${REPODY_RELEASE}, tag ${IMAGE_TAG})`);
  run("helm", [
    "upgrade",
    "--install",
    REPODY_RELEASE,
    CHART_REPODY,
    "-n",
    NS,
    "-f",
    path.join(CHART_REPODY, "values.yaml"),
    "-f",
    VALUES_STAGING,
    ...helmImageSets(),
    "--timeout",
    "25m",
    "--wait",
  ]);
}

function deployArgo() {
  heading("Registering Argo CD Applications");
  run("kubectl", ["apply", "-n", "argocd", "-f", path.join(ARGO_DIR, "repody-project.yaml")]);
  run("kubectl", ["apply", "-n", "argocd", "-f", path.join(ARGO_DIR, "repody-staging.application.yaml")]);
  console.error(`
Argo CD app registered. Sync when values-staging.yaml and images are ready:
  argocd app sync repody-staging
`);
}

heading("Repody staging deploy");
ensureNamespace();

if (useArgo) {
  deployArgo();
} else {
  deployHelm();
  console.error(`
Staging Helm release installed in namespace ${NS}.
Repody: ${REPODY_RELEASE} | tag: ${IMAGE_TAG}

Next: configure DNS/TLS and ensure the external VLM endpoint in values-staging.yaml
is reachable from worker pods. Add AUDIT_VLLM_API_KEY to repody-runtime-secrets
when the endpoint requires auth.
`);
}
