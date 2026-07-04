#!/usr/bin/env node
/**
 * k3s client cluster — bundled profile (Vault + ESO + Helm + Ingress + OTEL).
 * Treats k3d/k3s as a real client cluster: no OpenShift Routes, no host-network VLM hacks.
 *
 *   node deploy/scripts/k3s-client-bundled.mjs <command>
 *
 * Commands: preflight | clean | cluster | bootstrap | seed | observability | images | deploy | verify | all
 * Flags: --dry-run --skip-images --skip-clean
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildLabVaultKvs } from "./lib/lab-seed.mjs";
import { createTlsSecret } from "./lib/lab-tls.mjs";
import { ensureMigrationsJob } from "./lib/migrations-job.mjs";
import { bundledAuthValuesYaml, bundledRepodyValuesYaml } from "./lib/bundled-values.mjs";
import { readPackageVersion, parseArgs, log, fail, sleep } from "./lib/cli.mjs";
import { createVaultEsoHelpers } from "./lib/vault-eso.mjs";
import { createVaultBootstrap } from "./lib/vault-bootstrap.mjs";
import { commandFor, resolveExecutable } from "./runtime-env.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const runtimeDir = path.join(root, "deploy/client/lab/.runtime-k3s");
const CLUSTER = process.env.REPODY_K3S_CLUSTER ?? "repody-client";
const REGISTRY_NAME = "repody-registry.localhost";
const REGISTRY_PORT = process.env.REPODY_K3S_REGISTRY_PORT ?? "5050";
const LB_HTTP_PORT = process.env.REPODY_K3S_HTTP_PORT ?? "8080";
const LB_HTTPS_PORT = process.env.REPODY_K3S_HTTPS_PORT ?? "8443";
const DOMAIN = process.env.REPODY_CLIENT_DOMAIN ?? "repody.test";
const NS = {
  repody: "repody",
  vault: "vault",
  eso: "external-secrets",
  observability: "observability",
};

const args = parseArgs(process.argv);
const tag = (process.env.REPODY_IMAGE_TAG ?? readPackageVersion(root)).trim();

function run(cmd, cmdArgs, { dryRun = false, quiet = false, cwd = root, input, env } = {}) {
  if (dryRun) {
    console.log(`[dry-run] ${cmd} ${cmdArgs.join(" ")}`);
    return { status: 0, stdout: "", stderr: "" };
  }
  const useShell = process.platform === "win32" && /\.(cmd|bat)$/i.test(cmd);
  return spawnSync(cmd, cmdArgs, {
    cwd,
    encoding: "utf8",
    stdio: quiet ? "pipe" : "inherit",
    shell: useShell,
    input,
    env: { ...process.env, ...env },
  });
}

function k3d(cmdArgs, opts = {}) {
  return run(resolveExecutable("k3d"), cmdArgs, opts);
}

function kubectl(cmdArgs, opts = {}) {
  return run(resolveExecutable("kubectl"), cmdArgs, { ...opts, env: { ...process.env, KUBECONFIG: kubeconfigPath() } });
}

function kubectlOut(cmdArgs) {
  const result = kubectl(cmdArgs, { quiet: true });
  if (result.status !== 0) return "";
  return (result.stdout ?? "").trim();
}

function helm(cmdArgs, opts = {}) {
  return run(resolveExecutable("helm"), cmdArgs, { ...opts, env: { ...process.env, KUBECONFIG: kubeconfigPath() } });
}

const vaultEso = createVaultEsoHelpers({
  root,
  kubectl,
  kubectlOut,
  fail,
  sleep,
  repodyNamespace: NS.repody,
  vaultNamespace: NS.vault,
  runtimeDir,
});

const vaultBootstrap = createVaultBootstrap({
  exec: kubectl,
  getOut: kubectlOut,
  fail,
  sleep,
  vaultNamespace: NS.vault,
});

function kubeconfigPath() {
  const kubePath = path.join(runtimeDir, "kubeconfig");
  const out = k3d(["kubeconfig", "write", CLUSTER, "--output", kubePath], { quiet: true });
  if (out.status !== 0) fail("k3d kubeconfig write failed");
  // Windows Docker Desktop: host.docker.internal is often unreachable from the host shell.
  const content = readFileSync(kubePath, "utf8").replaceAll("host.docker.internal", "127.0.0.1");
  writeFileSync(kubePath, content, "utf8");
  return kubePath;
}

function registryPushHost() {
  return `localhost:${REGISTRY_PORT}`;
}

/** Hostname pods use to pull from the k3d-attached registry (see node registries.yaml). */
function registryPullHost() {
  return `k3d-${REGISTRY_NAME}:${REGISTRY_PORT}`;
}

function imageRepo() {
  return `${registryPullHost()}/repody`;
}

function clientHosts() {
  return {
    web: `app.${DOMAIN}`,
    api: `api.${DOMAIN}`,
    auth: `auth.${DOMAIN}`,
    files: `files.${DOMAIN}`,
  };
}

function preflight() {
  for (const tool of ["docker", "helm", "kubectl"]) {
    if (run(resolveExecutable(tool), ["version"], { quiet: true }).status !== 0) {
      fail(`Missing tool: ${tool}`);
    }
  }
  if (k3d(["version"], { quiet: true }).status !== 0) {
    fail("Missing k3d — install: winget install k3d.k3d");
  }
  log("preflight", "ok: docker, k3d, kubectl, helm");
}

function clean() {
  k3d(["cluster", "delete", CLUSTER], { quiet: true });
  k3d(["registry", "delete", REGISTRY_NAME], { quiet: true });
  if (existsSync(runtimeDir)) rmSync(runtimeDir, { recursive: true, force: true });
  log("clean", `removed cluster ${CLUSTER} and registry ${REGISTRY_NAME}`);
}

function k3dClusterExists() {
  const result = k3d(["cluster", "list", "-o", "json"], { quiet: true });
  if (result.status !== 0) return false;
  try {
    return JSON.parse(result.stdout ?? "[]").some((c) => c.name === CLUSTER);
  } catch {
    return false;
  }
}

function cluster() {
  mkdirSync(runtimeDir, { recursive: true });
  if (k3dClusterExists() && !args.flags.has("--force-recreate")) {
    kubeconfigPath();
    log("cluster", `using existing cluster ${CLUSTER}`);
    return;
  }
  k3d(["registry", "create", REGISTRY_NAME, "--port", REGISTRY_PORT], { quiet: true });
  const create = k3d([
    "cluster",
    "create",
    CLUSTER,
    "--registry-use",
    `k3d-${REGISTRY_NAME}:${REGISTRY_PORT}`,
    "-p",
    `${LB_HTTP_PORT}:80@loadbalancer`,
    "-p",
    `${LB_HTTPS_PORT}:443@loadbalancer`,
    "--agents",
    "1",
    "--wait",
  ]);
  if (create.status !== 0) fail("k3d cluster create failed");
  kubeconfigPath();
  log("cluster", `k3s ready (${CLUSTER}) — Traefik on :${LB_HTTP_PORT}/:${LB_HTTPS_PORT}`);
}

function helmRepoAdd(name, url) {
  helm(["repo", "add", name, url, "--force-update"], { quiet: true });
  helm(["repo", "update", name], { quiet: true });
}

function ensureNamespace(name) {
  kubectl(["apply", "-f", "-"], {
    input: `apiVersion: v1\nkind: Namespace\nmetadata:\n  name: ${name}\n`,
    quiet: true,
  });
}

function waitForPods(ns, selector, timeoutSec = 300) {
  const deadline = Date.now() + timeoutSec * 1000;
  while (Date.now() < deadline) {
    const result = kubectl(
      ["wait", "--for=condition=Ready", "pod", "-l", selector, "-n", ns, `--timeout=30s`],
      { quiet: true },
    );
    if (result.status === 0) return true;
    sleep(3000);
  }
  return false;
}

function bootstrap() {
  kubeconfigPath();
  helmRepoAdd("hashicorp", "https://helm.releases.hashicorp.com");
  helmRepoAdd("external-secrets", "https://charts.external-secrets.io");

  ensureNamespace(NS.vault);
  ensureNamespace(NS.eso);
  ensureNamespace(NS.repody);
  kubectl(["apply", "-f", "deploy/client/namespace.example.yaml"], { dryRun: args.flags.has("--dry-run") });

  helm(
    [
      "upgrade",
      "--install",
      "vault",
      "hashicorp/vault",
      "-n",
      NS.vault,
      "-f",
      "deploy/client/lab/vault/values.yaml",
      "--wait",
      "--timeout",
      "10m",
    ],
    { dryRun: args.flags.has("--dry-run") },
  );

  helm(
    [
      "upgrade",
      "--install",
      "external-secrets",
      "external-secrets/external-secrets",
      "-n",
      NS.eso,
      "--set",
      "installCRDs=true",
      "--wait",
      "--timeout",
      "10m",
    ],
    { dryRun: args.flags.has("--dry-run") },
  );

  if (!args.flags.has("--dry-run")) {
    kubectl(["apply", "-f", "deploy/client/lab/manifests/vault-auth-rbac.yaml"]);
    vaultBootstrap.applyVaultAuthTokenSecret();
    if (!waitForPods(NS.vault, "app.kubernetes.io/name=vault", 300)) {
      fail("Vault pod did not become Ready");
    }
    vaultBootstrap.configureVault();
    kubectl(["apply", "-f", "deploy/client/lab/manifests/clustersecretstore.yaml"]);
  }
  log("bootstrap", "Vault + External Secrets Operator ready");
}

function dockerConfigForLocalRegistry() {
  const pullHost = registryPullHost();
  return JSON.stringify({
    auths: {
      [pullHost]: {},
      [registryPushHost()]: {},
    },
  });
}

function seed() {
  kubeconfigPath();
  const { dataKv, runtimeKv } = buildLabVaultKvs({ dockerConfigJson: dockerConfigForLocalRegistry() });
  if (!args.flags.has("--dry-run")) {
    vaultEso.putVaultKv("secret/repody/production/data", dataKv);
    vaultEso.putVaultKv("secret/repody/production", runtimeKv);
    vaultEso.applyExternalSecrets(vaultEso.bundledExternalSecretFiles);
    vaultEso.waitExternalSecrets();
  }
  log("seed", "Vault KV seeded; ExternalSecrets synced");
}

function observability() {
  kubeconfigPath();
  ensureNamespace(NS.observability);
  helmRepoAdd("open-telemetry", "https://open-telemetry.github.io/opentelemetry-helm-charts");
  helm(
    [
      "upgrade",
      "--install",
      "otel-collector",
      "open-telemetry/opentelemetry-collector",
      "-n",
      NS.observability,
      "-f",
      "deploy/client/lab/manifests/observability-otel.yaml",
      "--wait",
      "--timeout",
      "8m",
    ],
    { dryRun: args.flags.has("--dry-run") },
  );
  log("observability", "OpenTelemetry Collector deployed (upstream Helm chart)");
}

function images() {
  if (args.flags.has("--skip-images")) {
    log("images", "skipped (--skip-images)");
    return;
  }
  kubeconfigPath();
  process.env.REPODY_IMAGE_REGISTRY = `${registryPushHost()}/repody`;
  process.env.REPODY_IMAGE_TAG = tag;
  const result = run(resolveExecutable("node"), ["deploy/scripts/build-images.mjs", "--push"], { cwd: root });
  if (result.status !== 0) fail("image build/push failed");
  log("images", `pushed ${imageRepo()}/*:${tag}`);
}

function writeRenderedValues(hosts) {
  mkdirSync(runtimeDir, { recursive: true });
  const content = bundledRepodyValuesYaml({
    imageRepo: imageRepo(),
    tag,
    hosts,
    vlmUrl: process.env.REPODY_VLM_URL ?? "http://127.0.0.1:65535/v1",
    ingressClassName: "traefik",
    vlmServedModel: "numind/NuExtract3",
  });
  const outPath = path.join(runtimeDir, "values.rendered.yaml");
  writeFileSync(outPath, content, "utf8");
  const authPath = path.join(runtimeDir, "values.auth.rendered.yaml");
  writeFileSync(authPath, bundledAuthValuesYaml({ authHost: hosts.auth, className: "traefik" }), "utf8");
  return { outPath, authPath };
}

function ensureMigrations(backendImage) {
  if (args.flags.has("--dry-run")) return;
  ensureMigrationsJob({
    apply: kubectl,
    getOut: kubectlOut,
    fail,
    namespace: NS.repody,
    backendImage,
  });
}

function deploy() {
  kubeconfigPath();
  const hosts = clientHosts();
  const rendered = writeRenderedValues(hosts);
  if (!args.flags.has("--dry-run")) {
    createTlsSecret({
      apply: kubectl,
      run,
      runtimeDir,
      domain: DOMAIN,
      sanHosts: [hosts.web, hosts.api, hosts.auth, hosts.files],
      namespace: NS.repody,
      fail,
    });
  }

  run(commandFor("pnpm"), ["helm:deps:update"], { cwd: root });

  helm(
    [
      "upgrade",
      "--install",
      "repody-data",
      "deploy/helm/repody-data",
      "-n",
      NS.repody,
      "-f",
      "deploy/helm/repody-data/values.yaml",
      "-f",
      "deploy/client/bundled/values.data.yaml",
      "-f",
      "deploy/client/lab/values.data.openshift-local.yaml",
      "--wait",
      "--timeout",
      "20m",
    ],
    { dryRun: args.flags.has("--dry-run") },
  );

  helm(
    [
      "upgrade",
      "--install",
      "repody-auth",
      "deploy/helm/repody-auth",
      "-n",
      NS.repody,
      "-f",
      "deploy/helm/repody-auth/values.yaml",
      "-f",
      "deploy/client/lab/values.auth.openshift-local.yaml",
      "-f",
      rendered.authPath,
      "--wait",
      "--timeout",
      "15m",
    ],
    { dryRun: args.flags.has("--dry-run") },
  );

  const backendImage = `${imageRepo()}/repody-backend:${tag}`;
  if (!args.flags.has("--dry-run")) ensureMigrations(backendImage);

  helm(
    [
      "upgrade",
      "--install",
      "repody",
      "deploy/helm/repody",
      "-n",
      NS.repody,
      "-f",
      "deploy/helm/repody/values.yaml",
      "-f",
      "deploy/helm/repody/values-common.yaml",
      "-f",
      "deploy/client/values-bundled.example.yaml",
      "-f",
      "deploy/client/values-enterprise.example.yaml",
      "-f",
      "deploy/values/k3s.yaml",
      "-f",
      "deploy/client/lab/values.k3s-bundled.yaml",
      "-f",
      "deploy/client/lab/values.openshift-local.crc.yaml",
      "-f",
      rendered.outPath,
      "--wait",
      "--timeout",
      "30m",
    ],
    { dryRun: args.flags.has("--dry-run") },
  );

  log(
    "deploy",
    [
      "Ingress (Traefik):",
      `  Web:   https://${hosts.web}`,
      `  API:   https://${hosts.api}`,
      `  Auth:  https://${hosts.auth}`,
      `  Files: https://${hosts.files}`,
      "",
      "Add to hosts file (127.0.0.1):",
      `  ${hosts.web} ${hosts.api} ${hosts.auth} ${hosts.files}`,
      "",
      `HTTPS via Traefik load balancer port ${LB_HTTPS_PORT} (not 443 — avoids host conflicts).`,
    ].join("\n"),
  );
}

async function verify() {
  kubeconfigPath();
  const hosts = clientHosts();
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const resolve = (host) => ["--resolve", `${host}:${LB_HTTPS_PORT}:127.0.0.1`];

  if (run(resolveExecutable("node"), ["deploy/scripts/client-integration-check.mjs"], { cwd: root }).status !== 0) {
    fail("client integration check failed");
  }

  const otelWait = kubectl(
    ["wait", "--for=condition=available", "deployment/otel-collector-opentelemetry-collector", "-n", NS.observability, "--timeout=120s"],
    { quiet: true },
  );
  if (otelWait.status !== 0) {
    const fallback = kubectl(
      ["wait", "--for=condition=available", "deployment", "-l", "app.kubernetes.io/instance=otel-collector", "-n", NS.observability, "--timeout=120s"],
      { quiet: true },
    );
    if (fallback.status !== 0) fail("otel-collector deployment not available");
  }
  if (!waitForPods(NS.repody, "app.kubernetes.io/component=control", 120)) {
    fail("repody-api pods not Ready");
  }

  const apiUrl = `https://${hosts.api}:${LB_HTTPS_PORT}/v1/healthz/live`;
  let ok = false;
  for (let i = 0; i < 24; i++) {
    const result = run(curl, [...resolve(hosts.api), "-kfsS", "--max-time", "8", apiUrl], { quiet: true });
    if (result.status === 0) {
      ok = true;
      break;
    }
    sleep(5000);
  }
  if (!ok) fail(`API health check failed: ${apiUrl}`);

  const webUrl = `https://${hosts.web}:${LB_HTTPS_PORT}`;
  const webResult = run(curl, [...resolve(hosts.web), "-kfsS", "--max-time", "8", webUrl], {
    quiet: true,
  });
  if (webResult.status !== 0) fail(`Web ingress check failed: ${webUrl}`);

  log(
    "verify",
    [
      "Client bundled deploy healthy on k3s.",
      `API: ${apiUrl}`,
      "Run extraction E2E after pointing config.vllmBaseUrl at a client-managed VLM (REPODY_VLM_URL).",
    ].join("\n"),
  );
}

const steps = {
  preflight,
  clean: () => {
    if (!args.flags.has("--skip-clean")) clean();
  },
  cluster,
  bootstrap,
  seed,
  observability,
  images,
  deploy,
  verify,
  all: async () => {
    preflight();
    if (!args.flags.has("--skip-clean")) clean();
    cluster();
    bootstrap();
    seed();
    observability();
    images();
    deploy();
    await verify();
  },
};

const step = steps[args.cmd];
if (!step) {
  fail(`unknown command: ${args.cmd}`);
}
Promise.resolve(step()).catch((err) => fail(err?.message ?? String(err)));
