#!/usr/bin/env node
/**
 * Deploy assets check with the standard tools:
 *   helm lint, helm template | kubeconform (Kubernetes schemas), kubectl kustomize,
 *   docker buildx bake --print (bake variable validation), docker compose config for the
 *   VPS stack (every required variable from deploy/vps/env.example), the deploy's own gate on it
 *   (deploy/vps/check_compose.py, here at review time too), the docs link check, and that
 *   backup.sh restores into the stack's own Postgres image.
 *
 * kubeconform runs from its official image when the binary is not installed.
 */
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

const CHART = "deploy/helm/repody";
const PRODUCTION_VALUES = `${CHART}/values-production.yaml.example`;

function run(cmd, args, input, env) {
  return spawnSync(cmd, args, {
    encoding: "utf8",
    input,
    env: env ? { ...process.env, ...env } : process.env,
    maxBuffer: 64 * 1024 * 1024,
  });
}

/** deploy/vps/env.example as variables, blanks filled, so `${VAR:?}` can resolve. */
function stackEnv() {
  const entries = readFileSync("deploy/vps/env.example", "utf8")
    .split(/\r?\n/)
    .filter((line) => /^[A-Z][A-Z0-9_]*=/.test(line))
    .map((line) => line.split(/=(.*)/s, 2))
    .map(([key, value]) => [key, value || "deploy-check"]);
  // Each deploy writes REPODY_VERSION to release.env beside .env.
  return { ...Object.fromEntries(entries), REPODY_VERSION: "0.0.0" };
}

function kubeconform(manifests) {
  const args = ["-strict", "-summary", "-"];
  const local = run("kubeconform", ["-v"]);
  return local.status === 0
    ? run("kubeconform", args, manifests)
    : run("docker", ["run", "--rm", "-i", "ghcr.io/yannh/kubeconform:v0.7.0", ...args], manifests);
}

const PYTHON = process.platform === "win32" ? "python" : "python3";

/** The stack as the deploy renders it, through the gate deploy.yml runs before starting it. */
function stackGate() {
  const config = run(
    "docker",
    ["compose", "-f", "deploy/vps/compose.yaml", "config", "--format", "json"],
    undefined,
    stackEnv(),
  );
  return config.status === 0 ? run(PYTHON, ["deploy/vps/check_compose.py"], config.stdout) : config;
}

/** The gate itself refuses a stack that reaches outside (a privileged service, the host's paths). */
function gateRefuses() {
  const escaping = JSON.stringify({
    services: {
      web: { privileged: true, volumes: [{ type: "bind", source: "/var/run/docker.sock" }] },
    },
  });
  const result = run(PYTHON, ["deploy/vps/check_compose.py"], escaping);
  return result.status === 1 && result.stderr.includes("docker.sock")
    ? { status: 0 }
    : {
        status: 1,
        stderr: `check_compose.py let an escaping stack through:
${result.stderr}`,
      };
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
  [
    "compose config (VPS stack)",
    () =>
      run(
        "docker",
        ["compose", "-f", "deploy/vps/compose.yaml", "config", "-q"],
        undefined,
        stackEnv(),
      ),
  ],
  ["the deploy's gate passes the VPS stack (check_compose.py)", stackGate],
  ["the deploy's gate refuses an escaping stack", gateRefuses],
  ["docs links and commands", () => run("node", ["deploy/scripts/check-command-docs.mjs"])],
  ["backup restore test uses the stack's Postgres", samePostgres],
];

/** Dependabot updates compose.yaml, not the image pinned in backup.sh: they must not drift. */
function samePostgres() {
  const stack = readFileSync("deploy/vps/compose.yaml", "utf8").match(/image: (postgres:\S+)/)?.[1];
  const backup = readFileSync("deploy/vps/backup.sh", "utf8").match(
    /POSTGRES_IMAGE="([^"]+)"/,
  )?.[1];
  return stack && stack === backup
    ? { status: 0 }
    : { status: 1, stderr: `compose.yaml runs ${stack}, backup.sh restores into ${backup}` };
}

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
