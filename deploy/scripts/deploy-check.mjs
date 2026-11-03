#!/usr/bin/env node
/**
 * Deploy assets check with the standard tools:
 *   helm lint, helm template | kubeconform (Kubernetes schemas), kubectl kustomize,
 *   docker buildx bake --print (bake variable validation), and the docs link check.
 *
 * kubeconform runs from its official image when the binary is not installed.
 */
import { spawnSync } from "node:child_process";

const CHART = "deploy/helm/repody";
const PRODUCTION_VALUES = `${CHART}/values-production.yaml.example`;

function run(cmd, args, input) {
  return spawnSync(cmd, args, { encoding: "utf8", input, maxBuffer: 64 * 1024 * 1024 });
}

function kubeconform(manifests) {
  const args = ["-strict", "-summary", "-"];
  const local = run("kubeconform", ["-v"]);
  return local.status === 0
    ? run("kubeconform", args, manifests)
    : run("docker", ["run", "--rm", "-i", "ghcr.io/yannh/kubeconform:v0.7.0", ...args], manifests);
}

const steps = [
  ["helm lint", () => run("helm", ["lint", CHART, "-f", PRODUCTION_VALUES])],
  [
    "helm template | kubeconform (defaults)",
    () => {
      const rendered = run("helm", ["template", "repody", CHART]);
      return rendered.status === 0 ? kubeconform(rendered.stdout) : rendered;
    },
  ],
  [
    "helm template | kubeconform (production example)",
    () => {
      const rendered = run("helm", ["template", "repody", CHART, "-f", PRODUCTION_VALUES]);
      return rendered.status === 0 ? kubeconform(rendered.stdout) : rendered;
    },
  ],
  ["kustomize CloudNativePG", () => run("kubectl", ["kustomize", "deploy/managed/cloudnativepg"])],
  ["bake --print", () => run("docker", ["buildx", "bake", "-f", "docker-bake.hcl", "--print"])],
  ["docs links and commands", () => run("node", ["deploy/scripts/check-command-docs.mjs"])],
];

let failed = false;
for (const [label, check] of steps) {
  const result = check();
  if (result.status === 0) {
    console.error(`ok: ${label}`);
    continue;
  }
  failed = true;
  console.error(`failed: ${label}\n${`${result.stdout ?? ""}${result.stderr ?? ""}`.trimEnd()}`);
}
process.exit(failed ? 1 : 0);
