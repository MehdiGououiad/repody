#!/usr/bin/env node
/**
 * OpenShift Local (CRC) — client promotion harness (Vault + ESO + bundled Helm).
 *
 *   node deploy/scripts/openshift-local-promote.mjs <command> [flags]
 *
 * Commands: preflight | clean | registry | images | bootstrap | seed | deploy | vlm | verify | all
 * Flags: --dry-run --skip-images --skip-vlm --skip-clean --vlm
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { commandFor, resolveExecutable } from "./runtime-env.mjs";
import { readPackageVersion, parseArgs, log, fail, sleep } from "./lib/cli.mjs";
import { createVaultEsoHelpers } from "./lib/vault-eso.mjs";
import { createVaultBootstrap } from "./lib/vault-bootstrap.mjs";
import { buildLabVaultKvs } from "./lib/lab-seed.mjs";
import { ensureMigrationsJob } from "./lib/migrations-job.mjs";
import { bundledAuthValuesYaml, bundledRepodyValuesYaml } from "./lib/bundled-values.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const runtimeDir = path.join(root, "deploy/client/lab/.runtime");
const NS = { repody: "repody", vault: "vault", eso: "external-secrets" };

const args = parseArgs(process.argv);
const tag = (process.env.REPODY_IMAGE_TAG ?? readPackageVersion(root)).trim();

function resolveOc() {
  const fromEnv = process.env.CRC_OC?.trim() || process.env.OC?.trim();
  if (fromEnv && existsSync(fromEnv)) return fromEnv;
  const candidates = [
    path.join(os.homedir(), ".crc", "bin", "oc", "oc.exe"),
    path.join(os.homedir(), ".crc", "bin", "oc.exe"),
    path.join(os.homedir(), ".crc", "bin", "oc", "oc"),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return resolveExecutable("oc");
}

function run(cmd, cmdArgs, { dryRun = false, quiet = false, cwd = root, input } = {}) {
  if (dryRun) {
    console.log(`[dry-run] ${cmd} ${cmdArgs.join(" ")}`);
    return { status: 0, stdout: "", stderr: "" };
  }
  const result = spawnSync(cmd, cmdArgs, {
    cwd,
    encoding: "utf8",
    stdio: quiet ? "pipe" : "inherit",
    shell: false,
    input,
    env: process.env,
  });
  if (quiet && result.status !== 0) {
    const err = (result.stderr ?? result.stdout ?? "").trim();
    if (err) console.error(err);
  }
  return result;
}

function oc(cmdArgs, opts = {}) {
  return run(resolveOc(), cmdArgs, opts);
}

function ocOut(cmdArgs) {
  const result = oc(cmdArgs, { quiet: true });
  if (result.status !== 0) return "";
  return (result.stdout ?? "").trim();
}

const vaultEso = createVaultEsoHelpers({
  root,
  kubectl: oc,
  kubectlOut: ocOut,
  fail,
  sleep,
  repodyNamespace: NS.repody,
  vaultNamespace: NS.vault,
  runtimeDir,
});

const vaultBootstrap = createVaultBootstrap({
  exec: oc,
  getOut: ocOut,
  fail,
  sleep,
  vaultNamespace: NS.vault,
});

function helm(cmdArgs, opts = {}) {
  return run(resolveExecutable("helm"), cmdArgs, opts);
}

function requireCluster() {
  const who = ocOut(["whoami"]);
  if (!who) fail("oc is not logged in. Run: crc oc-env | Invoke-Expression; oc login -u kubeadmin");
  return who;
}

function appsDomain() {
  if (process.env.REPODY_APPS_DOMAIN?.trim()) return process.env.REPODY_APPS_DOMAIN.trim();
  const domain = ocOut([
    "get",
    "ingresses.config",
    "cluster",
    "-o",
    "jsonpath={.spec.domain}",
  ]);
  if (!domain) fail("Could not read cluster apps domain (ingresses.config/cluster).");
  return domain;
}

function routeHosts(domain) {
  const prefix = process.env.REPODY_ROUTE_PREFIX?.trim() || "repody";
  return {
    web: `${prefix}-web.${domain}`,
    api: `${prefix}-api.${domain}`,
    auth: `${prefix}-auth.${domain}`,
    files: `${prefix}-files.${domain}`,
  };
}

function internalRegistry() {
  return "image-registry.openshift-image-registry.svc:5000/repody";
}

function registryRouteHost() {
  return ocOut([
    "get",
    "route",
    "default-route",
    "-n",
    "openshift-image-registry",
    "-o",
    "jsonpath={.spec.host}",
  ]);
}

function hostVlmUrl() {
  if (process.platform === "win32") {
    const result = spawnSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } | Sort-Object InterfaceMetric | Select-Object -First 1 -ExpandProperty IPAddress)",
      ],
      { encoding: "utf8" },
    );
    const ip = (result.stdout ?? "").trim();
    if (ip) return `http://${ip}:8081/v1`;
  }
  return "http://host.crc.testing:8081/v1";
}

function writeRenderedValues(hosts) {
  mkdirSync(runtimeDir, { recursive: true });
  const registry = internalRegistry();
  const openshiftOverlay = `global:
  openshift:
    enabled: true
    routes:
      enabled: false

ingress:
  annotations:
    route.openshift.io/termination: edge
`;
  const content = `${bundledRepodyValuesYaml({
    imageRepo: registry,
    tag,
    hosts,
    vlmUrl: hostVlmUrl(),
    vlmServedModel: "nuextract3-q4_k_m",
  })}
${openshiftOverlay}
externalObjectStorage:
  publicEndpoint: ${hosts.files}
`;
  const outPath = path.join(runtimeDir, "values.rendered.yaml");
  writeFileSync(outPath, content, "utf8");
  const authPath = path.join(runtimeDir, "values.auth.rendered.yaml");
  writeFileSync(
    authPath,
    `${bundledAuthValuesYaml({ authHost: hosts.auth })}
global:
  openshift:
    enabled: true
    routes:
      enabled: false

ingress:
  annotations:
    route.openshift.io/termination: edge
`,
    "utf8",
  );
  return { outPath, authPath };
}

function preflight() {
  for (const tool of ["helm", "docker"]) {
    const probe = run(resolveExecutable(tool), ["version"], { quiet: true });
    if (probe.status !== 0) fail(`Missing tool: ${tool}`);
  }
  if (run(resolveOc(), ["version", "--client"], { quiet: true }).status !== 0) {
    fail("Missing oc — run: crc oc-env | Invoke-Expression");
  }
  log("preflight", "ok: helm, docker, oc available");
}

function stripExternalSecretFinalizers(ns) {
  const names = ocOut(["get", "externalsecret", "-n", ns, "-o", "jsonpath={.items[*].metadata.name}"]);
  for (const name of names.split(/\s+/).filter(Boolean)) {
    oc(
      [
        "patch",
        "externalsecret",
        name,
        "-n",
        ns,
        "--type=merge",
        "-p",
        '{"metadata":{"finalizers":null}}',
      ],
      { quiet: true },
    );
  }
}

function clean() {
  if (args.flags.has("--skip-clean")) {
    log("clean", "skipped (--skip-clean)");
    return;
  }
  oc(["delete", "validatingwebhookconfiguration", "externalsecret-validate", "--ignore-not-found"], {
    dryRun: args.flags.has("--dry-run"),
    quiet: true,
  });
  for (const ns of [NS.repody, NS.vault, NS.eso]) {
    if (args.flags.has("--dry-run")) continue;
    stripExternalSecretFinalizers(ns);
    oc(["delete", "externalsecret", "--all", "-n", ns, "--ignore-not-found", "--wait=false"], {
      quiet: true,
    });
  }
  for (const project of [NS.repody, NS.vault, NS.eso]) {
    oc(["delete", "project", project, "--ignore-not-found", "--wait=false"], {
      dryRun: args.flags.has("--dry-run"),
    });
  }
  if (!args.flags.has("--dry-run")) waitForNamespacesGone([NS.repody, NS.vault, NS.eso]);
  log("clean", "namespace delete completed");
}

function waitForNamespacesGone(names, timeoutSec = 300) {
  const deadline = Date.now() + timeoutSec * 1000;
  while (Date.now() < deadline) {
    const remaining = names.filter((name) => oc(["get", "project", name], { quiet: true }).status === 0);
    if (remaining.length === 0) return;
    for (const name of remaining) {
      stripExternalSecretFinalizers(name);
      oc(
        ["patch", "namespace", name, "--type=json", "-p", '[{"op":"replace","path":"/spec/finalizers","value":[]}]'],
        { quiet: true },
      );
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5000);
  }
  const stuck = names.filter((name) => oc(["get", "project", name], { quiet: true }).status === 0);
  if (stuck.length) fail(`Namespaces still terminating: ${stuck.join(", ")}`);
}

function registrySetup() {
  requireCluster();
  oc([
    "patch",
    "configs.imageregistry/cluster",
    "--type",
    "merge",
    "-p",
    JSON.stringify({ spec: { managementState: "Managed" } }),
  ], { dryRun: args.flags.has("--dry-run") });

  const host = registryRouteHost();
  if (!host && !args.flags.has("--dry-run")) {
    fail("OpenShift image registry route not found — wait for CRC to finish starting.");
  }

  const user = ocOut(["whoami"]) || "kubeadmin";
  const token = ocOut(["whoami", "-t"]);
  if (!token && !args.flags.has("--dry-run")) fail("oc whoami -t returned empty token");

  if (!args.flags.has("--dry-run")) {
    const auth = Buffer.from(`${user}:${token}`, "utf8").toString("base64");
    const dockerConfig = JSON.stringify({
      auths: {
        [host]: { username: user, password: token, auth, email: "repody-lab@local" },
        [internalRegistry()]: { username: user, password: token, auth, email: "repody-lab@local" },
      },
    });
    mkdirSync(runtimeDir, { recursive: true });
    writeFileSync(path.join(runtimeDir, "registry-dockerconfig.json"), dockerConfig, "utf8");
    const login = run("docker", ["login", "-u", user, "--password-stdin", host], {
      input: token,
      quiet: true,
    });
    if (login.status !== 0) fail(`docker login to ${host} failed`);
  }

  log("registry", `ok: logged in to ${host ?? "<route>"}`);
}

function ensureImageStreams() {
  for (const name of ["repody-backend", "repody-web"]) {
    if (oc(["get", "imagestream", name, "-n", NS.repody], { quiet: true }).status !== 0) {
      const created = oc(["create", "imagestream", name, "-n", NS.repody], { quiet: true });
      if (created.status !== 0) fail(`failed to create ImageStream ${name} in ${NS.repody}`);
    }
  }
}

function buildImages() {
  if (args.flags.has("--skip-images")) {
    log("images", "skipped (--skip-images)");
    return;
  }
  requireCluster();
  ensureProject(NS.repody, "Repody");
  ensureImageStreams();
  registrySetup();
  const registryHost = registryRouteHost();
  process.env.REPODY_IMAGE_REGISTRY = registryHost ? `${registryHost}/repody` : internalRegistry();
  process.env.REPODY_IMAGE_TAG = tag;
  const result = run(commandFor("pnpm"), ["images:release"], { cwd: root });
  if (result.status !== 0) fail("pnpm images:release failed");
  log("images", `pushed ${process.env.REPODY_IMAGE_REGISTRY}/*:${tag}`);
}

function helmRepoAdd(name, url) {
  helm(["repo", "add", name, url, "--force-update"], { quiet: true });
  helm(["repo", "update", name], { quiet: true });
}

function waitForPods(ns, selector, timeoutSec = 300) {
  const result = oc(
    [
      "wait",
      "--for=condition=Ready",
      "pod",
      "-l",
      selector,
      "-n",
      ns,
      `--timeout=${timeoutSec}s`,
    ],
    { quiet: true },
  );
  return result.status === 0;
}

function ensureProject(name, displayName) {
  if (oc(["get", "project", name], { quiet: true }).status !== 0) {
    oc(["new-project", name, `--display-name=${displayName}`], { dryRun: args.flags.has("--dry-run") });
  }
  if (args.flags.has("--dry-run")) return;
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    const phase = ocOut(["get", "namespace", name, "-o", "jsonpath={.status.phase}"]);
    if (phase === "Active") return;
    sleep(2000);
  }
  fail(`namespace ${name} did not become Active`);
}

function bootstrap() {
  requireCluster();
  helmRepoAdd("hashicorp", "https://helm.releases.hashicorp.com");
  helmRepoAdd("external-secrets", "https://charts.external-secrets.io");

  ensureProject(NS.vault, "Repody Vault Lab");
  ensureProject(NS.eso, "External Secrets");
  ensureProject(NS.repody, "Repody");
  configureLabNamespace();

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
      "-f",
      "deploy/client/lab/vault/values.openshift.yaml",
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
    oc(["adm", "policy", "add-scc-to-user", "anyuid", "-z", "vault", "-n", NS.vault], { quiet: true });
    oc(["apply", "-f", "deploy/client/lab/manifests/vault-auth-rbac.yaml"]);
    vaultBootstrap.applyVaultAuthTokenSecret();
    if (!waitForPods(NS.vault, "app.kubernetes.io/name=vault", 240)) {
      fail("Vault pod did not reach Running");
    }
    vaultBootstrap.configureVault();
    oc(["apply", "-f", "deploy/client/lab/manifests/clustersecretstore.yaml"]);
  }

  log("bootstrap", "Vault + External Secrets installed");
}

function configureLabNamespace() {
  oc(["apply", "-f", "deploy/client/namespace.example.yaml"], { dryRun: args.flags.has("--dry-run") });
}

function readDockerConfig() {
  const file = path.join(runtimeDir, "registry-dockerconfig.json");
  if (!existsSync(file)) registrySetup();
  return readFileSync(file, "utf8");
}

function seed() {
  requireCluster();
  const { dataKv, runtimeKv } = buildLabVaultKvs({ dockerConfigJson: readDockerConfig() });

  if (!args.flags.has("--dry-run")) {
    vaultEso.putVaultKv("secret/repody/production/data", dataKv);
    vaultEso.putVaultKv("secret/repody/production", runtimeKv);
    vaultEso.applyExternalSecrets(vaultEso.bundledExternalSecretFiles);
    vaultEso.waitExternalSecrets();
  }

  log("seed", "Vault KV seeded; ExternalSecrets applied");
}

function ensureMigrations(backendImage) {
  if (args.flags.has("--dry-run")) return;
  ensureMigrationsJob({
    apply: oc,
    getOut: ocOut,
    fail,
    namespace: NS.repody,
    backendImage,
  });
}

function deploy() {
  requireCluster();
  const hosts = routeHosts(appsDomain());
  const rendered = writeRenderedValues(hosts);

  run(commandFor("pnpm"), ["helm:deps:update"], { cwd: root });

  helm([
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
  ], { dryRun: args.flags.has("--dry-run") });

  helm([
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
  ], { dryRun: args.flags.has("--dry-run") });

  const backendImage = `${internalRegistry()}/repody-backend:${tag}`;
  if (!args.flags.has("--dry-run")) ensureMigrations(backendImage);

  helm([
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
    "deploy/values/openshift.yaml",
    "-f",
    "deploy/client/lab/values.openshift-local.yaml",
    "-f",
    "deploy/client/lab/values.openshift-local.crc.yaml",
    "-f",
    "deploy/client/lab/values.openshift-local.security.yaml",
    "-f",
    rendered.outPath,
    "--wait",
    "--timeout",
    "30m",
  ], { dryRun: args.flags.has("--dry-run") });

  log(
    "deploy",
    [
      "Routes (HTTPS):",
      `  Web:   https://${hosts.web}`,
      `  API:   https://${hosts.api}`,
      `  Auth:  https://${hosts.auth}`,
      `  Files: https://${hosts.files}`,
    ].join("\n"),
  );
}

function startVlm() {
  if (args.flags.has("--skip-vlm")) {
    log("vlm", "skipped (--skip-vlm)");
    return;
  }
  if (run(commandFor("pnpm"), ["llamacpp:serve"], { cwd: root }).status !== 0) {
    fail("pnpm llamacpp:serve failed");
  }
  if (run(commandFor("pnpm"), ["llamacpp:verify"], { cwd: root }).status !== 0) {
    fail("pnpm llamacpp:verify failed");
  }
  log("vlm", `host llama-server on :8081 (pods use ${hostVlmUrl()})`);
}

async function verifyRoutes() {
  requireCluster();
  const hosts = routeHosts(appsDomain());
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const apiUrl = `https://${hosts.api}/v1/healthz/live`;
  const webUrl = `https://${hosts.web}`;

  const deadline = Date.now() + 300_000;
  let apiOk = false;
  while (Date.now() < deadline) {
    if (run(curl, ["-kfsS", "--max-time", "12", apiUrl], { quiet: true }).status === 0) {
      apiOk = true;
      break;
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 8000);
  }
  if (!apiOk) fail(`API not healthy at ${apiUrl}`);

  const webProbe = run(
    curl,
    ["-kfsS", "--max-time", "12", "-o", os.devNull, "-w", "%{http_code}", webUrl],
    { quiet: true },
  );
  log(
    "verify",
    [`ok: ${apiUrl}`, `web: ${webUrl} (HTTP ${(webProbe.stdout ?? "").trim() || "?"})`].join("\n"),
  );
}

const handlers = {
  preflight,
  clean,
  registry: registrySetup,
  images: buildImages,
  bootstrap,
  seed,
  deploy,
  vlm: startVlm,
  verify: verifyRoutes,
  async all() {
    preflight();
    clean();
    buildImages();
    bootstrap();
    seed();
    deploy();
    if (args.flags.has("--vlm")) startVlm();
    await verifyRoutes();
    if (!args.flags.has("--dry-run")) {
      const check = run("node", ["deploy/scripts/check-openshift-client-ready.mjs", "--namespace", NS.repody], {
        quiet: true,
      });
      if (check.status !== 0) {
        console.error((check.stderr ?? check.stdout ?? "").trim());
        fail("client readiness check failed (run: node deploy/scripts/check-openshift-client-ready.mjs)");
      }
      log("client-ready", "production-shaped checks passed");
    }
  },
};

const handler = handlers[args.cmd];
if (!handler) {
  console.error(`Unknown command: ${args.cmd}`);
  console.error("Commands: preflight clean registry images bootstrap seed deploy vlm verify all");
  console.error("Flags: --dry-run --skip-images --skip-vlm --skip-clean --vlm");
  process.exit(1);
}

Promise.resolve(handler()).catch((error) => {
  fail(error instanceof Error ? error.message : String(error));
});
