#!/usr/bin/env node
/**
 * OpenShift client E2E — official kubectl + helm (no oc/k3d/Gitea).
 *
 * Infra: Harbor (Docker Compose on host), Vault, ESO, OTEL, Argo CD (official manifests).
 * Platform loop: build → push → seed → sync → verify → logs.
 *
 * @see https://goharbor.io/docs/main/install-config/run-installer-script/
 * @see https://argo-cd.readthedocs.io/en/stable/getting_started/
 * @see https://docs.openshift.com/container_platform/latest/applications/working_with_helm_charts/installing-a-helm-chart-on-openshift.html
 *
 *   node deploy/scripts/openshift-client-test.mjs <command> [flags]
 *
 * Commands:
 *   preflight | clean | infra | build | push | seed | register | sync |
 *   deploy | logs | verify | e2e | all
 *
 * Legacy aliases: platform, harbor, registry, images, observability, argocd
 *
 * Flags:
 *   --profile=bundled|external     default bundled
 *   --registry=harbor|openshift    default harbor
 *   --helm                         direct helm (default is GitOps / Argo CD)
 *   --clean                        tear down before all/e2e
 *   --dry-run --skip-images --skip-build --skip-vlm --vlm
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { commandFor, resolveExecutable } from "./runtime-env.mjs";
import { readPackageVersion, parseArgs, log, fail, sleep } from "./lib/cli.mjs";
import { createKubeCli } from "./lib/kube.mjs";
import { createVaultEsoHelpers } from "./lib/vault-eso.mjs";
import { createVaultBootstrap } from "./lib/vault-bootstrap.mjs";
import { buildLabVaultKvs } from "./lib/lab-seed.mjs";
import { ensureMigrationsJob } from "./lib/migrations-job.mjs";
import {
  bundledAuthValuesYaml,
  bundledRepodyValuesYaml,
  externalRepodyValuesYaml,
} from "./lib/bundled-values.mjs";
import { createHarborLab } from "./lib/harbor-lab.mjs";
import { createArgocdLab } from "./lib/argocd-lab.mjs";
import { createLabState } from "./lib/lab-state.mjs";
import { verifyJsonLogs } from "./lib/lab-logs.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const runtimeDir = path.join(root, "deploy/client/lab/.runtime");
const NS = {
  repody: "repody",
  vault: "vault",
  eso: "external-secrets",
  observability: "observability",
  harbor: "harbor",
  argocd: "argocd",
};

const args = parseArgs(process.argv);
const tag = (process.env.REPODY_IMAGE_TAG ?? readPackageVersion(root)).trim();
const state = createLabState(runtimeDir);

function flagValue(prefix) {
  for (const flag of args.flags) {
    if (flag.startsWith(`${prefix}=`)) return flag.slice(prefix.length + 1);
  }
  return null;
}

const profile = flagValue("--profile") === "external" ? "external" : "bundled";
const registryMode = flagValue("--registry") === "openshift" ? "openshift" : "harbor";
const gitops = !args.flags.has("--helm");
const dryRun = args.flags.has("--dry-run");

const kube = createKubeCli({ fail, sleep, env: process.env, dryRun });

function run(cmd, cmdArgs, opts = {}) {
  if (dryRun && !opts.allowReal) {
    console.log(`[dry-run] ${cmd} ${cmdArgs.join(" ")}`);
    return { status: 0, stdout: "", stderr: "" };
  }
  return spawnSync(cmd, cmdArgs, {
    cwd: opts.cwd ?? root,
    encoding: "utf8",
    stdio: opts.quiet ? "pipe" : "inherit",
    shell: opts.shell ?? false,
    input: opts.input,
    env: process.env,
  });
}

function helm(cmdArgs, opts = {}) {
  return run(resolveExecutable("helm"), cmdArgs, opts);
}

function helmRepoAdd(name, url) {
  helm(["repo", "add", name, url, "--force-update"], { quiet: true });
  helm(["repo", "update", name], { quiet: true });
}

const vaultEso = createVaultEsoHelpers({
  root,
  kubectl: kube.kubectl,
  kubectlOut: kube.kubectlOut,
  fail,
  sleep,
  repodyNamespace: NS.repody,
  vaultNamespace: NS.vault,
  runtimeDir,
});

const vaultBootstrap = createVaultBootstrap({
  exec: kube.kubectl,
  getOut: kube.kubectlOut,
  fail,
  sleep,
  vaultNamespace: NS.vault,
});

const harborLab = createHarborLab({
  fail,
  log,
  sleep,
  state,
  runtimeDir,
  dryRun,
});

const argocdLab = createArgocdLab({
  helm,
  kubectl: kube.kubectl,
  kubectlOut: kube.kubectlOut,
  fail,
  log,
  sleep,
  root,
  runtimeDir,
  state,
  dryRun,
});

function hosts() {
  return kube.routeHosts(kube.appsDomain());
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
  return process.env.REPODY_VLM_URL?.trim() || "http://host.crc.testing:8081/v1";
}

function openshiftOverlay() {
  return `global:
  openshift:
    enabled: true
    routes:
      enabled: false
`;
}

function imageRepo(hostList) {
  if (registryMode === "harbor") {
    const saved = state.get("harbor");
    if (saved?.clusterRegistry) return saved.clusterRegistry;
    if (saved?.registry) return saved.registry;
  }
  const fromEnv = process.env.REPODY_IMAGE_REGISTRY?.trim()?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (registryMode === "harbor") {
    return harborLab.harborRegistry(hostList);
  }
  return "image-registry.openshift-image-registry.svc:5000/repody";
}

function promoteGitValues(hostList, repo) {
  const appPromotedPath = path.join(root, "deploy/client/lab/values.openshift-local.promoted.yaml");
  const authPromotedPath = path.join(root, "deploy/client/lab/values.auth.openshift-local.promoted.yaml");

  const appContent = `${generatorHeader("openshift-client-test.mjs register")}
${bundledRepodyValuesYaml({
    imageRepo: repo,
    tag,
    hosts: hostList,
    vlmUrl: hostVlmUrl(),
    vlmServedModel: "nuextract3-q4_k_m",
    ingressClassName: "",
  })}
${openshiftOverlay()}`;

  const authContent = `${generatorHeader("openshift-client-test.mjs register")}
${bundledAuthValuesYaml({ authHost: hostList.auth, className: "" })}`;

  writeFileSync(appPromotedPath, appContent, "utf8");
  writeFileSync(authPromotedPath, authContent, "utf8");
  log("promote", `GitOps values written:\n  ${path.relative(root, appPromotedPath)}\n  ${path.relative(root, authPromotedPath)}`);
}

function generatorHeader(source) {
  return `# Generated by ${source} — commit and push before argocd sync.`;
}

function writeRenderedValues(hostList, repo) {
  mkdirSync(runtimeDir, { recursive: true });
  const generator = profile === "external" ? externalRepodyValuesYaml : bundledRepodyValuesYaml;
  const content = `${generator({
    imageRepo: repo,
    tag,
    hosts: hostList,
    vlmUrl: hostVlmUrl(),
    vlmServedModel: "nuextract3-q4_k_m",
    ingressClassName: "",
  })}
${openshiftOverlay()}`;
  const outPath = path.join(runtimeDir, "values.rendered.yaml");
  writeFileSync(outPath, content, "utf8");

  const authPath = path.join(runtimeDir, "values.auth.rendered.yaml");
  const authYaml = `${bundledAuthValuesYaml({ authHost: hostList.auth, className: "" })}
${openshiftOverlay()}`;
  writeFileSync(authPath, authYaml, "utf8");

  const inlineForArgo = content
    .split("\n")
    .filter((line) => !line.startsWith("#"))
    .map((l) => `        ${l}`)
    .join("\n");

  const authInline = authYaml
    .split("\n")
    .filter((line) => !line.startsWith("#"))
    .map((l) => `        ${l}`)
    .join("\n");

  return { outPath, authPath, inlineForArgo, authInline };
}

function ensureHelmDeps() {
  const dataCharts = path.join(root, "deploy/helm/repody-data/charts");
  if (!process.env.REPODY_HELM_DEPS && existsSync(dataCharts)) {
    return;
  }
  const result = run(commandFor("pnpm"), ["helm:deps:update"], { cwd: root, shell: process.platform === "win32" });
  if (result.status !== 0) fail("pnpm helm:deps:update failed");
}

function preflight() {
  const tools = [
    ["kubectl", ["version", "--client"]],
    ["helm", ["version"]],
    ["docker", ["version"]],
  ];
  for (const [tool, toolArgs] of tools) {
    if (run(resolveExecutable(tool), toolArgs, { quiet: true }).status !== 0) {
      fail(`Missing tool: ${tool}`);
    }
  }
  log(
    "preflight",
    `ok: kubectl, helm, docker | profile=${profile} registry=${registryMode} deploy=${gitops ? "gitops" : "helm"}`,
  );
}

function clean() {
  const infraOnly = args.flags.has("--infra");
  const appOnly = args.flags.has("--app");

  if (infraOnly && appOnly) fail("Use --infra or --app, not both");

  const appNs = [NS.repody];
  const infraNs = [NS.vault, NS.eso, NS.observability, NS.argocd];
  const targets = appOnly ? appNs : infraOnly ? infraNs : [...appNs, ...infraNs];

  kube.kubectl(
    ["delete", "validatingwebhookconfiguration", "externalsecret-validate", "--ignore-not-found"],
    { quiet: true, dryRun },
  );
  kube.deleteNamespaces(targets, { dryRun });

  if (!appOnly && registryMode === "harbor") {
    harborLab.stop?.();
  }

  if (!appOnly) {
    state.write({ harbor: undefined, argocd: undefined });
  }

  log("clean", `removed namespaces: ${targets.join(", ")}`);
}

function vaultReady() {
  return (
    kube.kubectlOut([
      "get",
      "deploy",
      "-l",
      "app.kubernetes.io/name=vault",
      "-n",
      NS.vault,
      "-o",
      "jsonpath={.items[0].status.readyReplicas}",
    ]) === "1"
  );
}

function platform() {
  kube.requireCluster();
  if (vaultReady() && !process.env.REPODY_FORCE_INFRA) {
    log("platform", "Vault + ESO already running (skip)");
    return;
  }

  helmRepoAdd("hashicorp", "https://helm.releases.hashicorp.com");
  helmRepoAdd("external-secrets", "https://charts.external-secrets.io");

  kube.ensureNamespace(NS.vault);
  kube.ensureNamespace(NS.eso);
  kube.ensureNamespace(NS.repody);
  kube.kubectl(["apply", "-f", "deploy/client/namespace.example.yaml"], { dryRun });

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
    { dryRun },
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
    { dryRun },
  );

  if (!dryRun) {
    kube.kubectl(["apply", "-f", "deploy/client/lab/manifests/vault-auth-rbac.yaml"]);
    vaultBootstrap.applyVaultAuthTokenSecret();
    if (!kube.waitForPods(NS.vault, "app.kubernetes.io/name=vault", 240)) {
      fail("Vault pod did not reach Ready");
    }
    vaultBootstrap.configureVault();
    kube.kubectl(["apply", "-f", "deploy/client/lab/manifests/clustersecretstore.yaml"]);
  }

  log("platform", "Vault + External Secrets ready");
}

function harbor() {
  if (registryMode !== "harbor") {
    log("harbor", "skipped (use --registry=harbor)");
    return null;
  }
  return harborLab.install();
}

function observability() {
  kube.requireCluster();
  const ready = kube.kubectlOut([
    "get",
    "deploy",
    "-l",
    "app.kubernetes.io/name=opentelemetry-collector",
    "-n",
    NS.observability,
    "-o",
    "jsonpath={.items[0].status.readyReplicas}",
  ]);
  if (ready === "1" && !process.env.REPODY_FORCE_INFRA) {
    log("observability", "OTEL collector already running (skip)");
    return;
  }

  kube.ensureNamespace(NS.observability);
  helmRepoAdd("open-telemetry", "https://open-telemetry.github.io/opentelemetry-helm-charts");
  const result = helm(
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
      "10m",
    ],
    { dryRun },
  );
  if (result.status !== 0) fail("OpenTelemetry collector install failed");
  log("observability", "OpenTelemetry collector ready");
}

function deployDataPlane() {
  if (profile === "bundled" && gitops) return;

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
    { dryRun },
  );
  if (profile === "external") {
    log("deploy", "external profile: data plane ready (simulated BYO)");
  }
}

function infra() {
  if (registryMode === "harbor") harbor();
  kube.requireCluster();
  platform();
  observability();
  argocdLab.install();
  if (profile === "external") deployDataPlane();
  log("infra", "lab infra ready — Harbor (Compose) + Argo CD (manifests) independent of Repody pushes");
}

function openshiftRegistrySetup() {
  kube.requireCluster();
  kube.kubectl(
    [
      "patch",
      "configs.imageregistry",
      "cluster",
      "--type",
      "merge",
      "-p",
      JSON.stringify({ spec: { managementState: "Managed" } }),
    ],
    { dryRun },
  );

  const host = kube.kubectlOut([
    "get",
    "route",
    "default-route",
    "-n",
    "openshift-image-registry",
    "-o",
    "jsonpath={.spec.host}",
  ]);
  if (!host && !dryRun) fail("OpenShift image registry route not found");

  const token =
    process.env.REPODY_REGISTRY_TOKEN?.trim() ||
    kube.kubectlOut(["create", "token", "default", "-n", "openshift-image-registry", "--duration=24h"]);
  const user = process.env.REPODY_REGISTRY_USER?.trim() || "kube:admin";

  if (!dryRun && host && token) {
    const auth = Buffer.from(`${user}:${token}`, "utf8").toString("base64");
    const dockerConfig = JSON.stringify({
      auths: {
        [host]: { username: user, password: token, auth, email: "repody-lab@local" },
        [`image-registry.openshift-image-registry.svc:5000/repody`]: {
          username: user,
          password: token,
          auth,
          email: "repody-lab@local",
        },
      },
    });
    mkdirSync(runtimeDir, { recursive: true });
    writeFileSync(path.join(runtimeDir, "registry-dockerconfig.json"), dockerConfig, "utf8");
    const login = run("docker", ["login", "-u", user, "--password-stdin", host], { input: token, quiet: true });
    if (login.status !== 0) fail(`docker login to ${host} failed`);
  }

  log("registry", `OpenShift internal registry ${host ?? "<pending>"}`);
  return {
    registry: host ? `${host}/repody` : "image-registry.openshift-image-registry.svc:5000/repody",
    host,
  };
}

function configureRegistryForPush() {
  if (registryMode === "harbor") {
    const saved = state.get("harbor");
    if (!saved?.host && !harborLab.isInstalled()) {
      fail("Harbor not running — run: node deploy/scripts/openshift-client-test.mjs harbor");
    }
    const info = saved?.host ? saved : harborLab.install();
    const password = info.password ?? process.env.REPODY_HARBOR_PASSWORD?.trim() ?? "Harbor12345";
    const pullHost = info.clusterHost ?? info.host;
    if (!dryRun) {
      harborLab.dockerLogin(info.host, harborLab.HARBOR_ADMIN, password);
      const dockerConfig = harborLab.writePullSecret(pullHost, harborLab.HARBOR_ADMIN, password);
      mkdirSync(runtimeDir, { recursive: true });
      writeFileSync(path.join(runtimeDir, "registry-dockerconfig.json"), dockerConfig, "utf8");
    }
    return info.registry;
  }
  const info = openshiftRegistrySetup();
  return info.registry;
}

function buildImages() {
  if (args.flags.has("--skip-build") || args.flags.has("--skip-images")) {
    log("build", "skipped");
    return;
  }
  const result = run(commandFor("pnpm"), ["images:build"], { cwd: root, shell: process.platform === "win32" });
  if (result.status !== 0) fail("pnpm images:build failed");
  log("build", `local images tagged for ${tag}`);
}

function pushImages() {
  if (args.flags.has("--skip-images")) {
    log("push", "skipped (--skip-images)");
    return;
  }
  kube.requireCluster();
  const repo = configureRegistryForPush();
  process.env.REPODY_IMAGE_REGISTRY = repo.replace(/\/repody-backend.*$/, "").replace(/\/repody$/, "") || repo;
  if (!process.env.REPODY_IMAGE_REGISTRY.endsWith("/repody")) {
    process.env.REPODY_IMAGE_REGISTRY = `${process.env.REPODY_IMAGE_REGISTRY.replace(/\/$/, "")}/repody`;
  }
  process.env.REPODY_IMAGE_TAG = tag;
  state.write({ lastPush: { registry: process.env.REPODY_IMAGE_REGISTRY, tag, at: new Date().toISOString() } });

  const result = run(commandFor("pnpm"), ["images:release"], { cwd: root, shell: process.platform === "win32" });
  if (result.status !== 0) fail("pnpm images:release failed");
  log("push", `pushed ${process.env.REPODY_IMAGE_REGISTRY}/*:${tag}`);
}

function readDockerConfig() {
  configureRegistryForPush();
  const file = path.join(runtimeDir, "registry-dockerconfig.json");
  return readFileSync(file, "utf8");
}

function seed() {
  kube.requireCluster();
  const esFiles =
    profile === "external"
      ? vaultEso.externalExternalSecretFiles
      : vaultEso.bundledExternalSecretFiles;
  const { dataKv, runtimeKv } = buildLabVaultKvs({ dockerConfigJson: readDockerConfig() });

  if (!dryRun) {
    if (profile === "bundled") {
      vaultEso.putVaultKv("secret/repody/production/data", dataKv);
    }
    vaultEso.putVaultKv("secret/repody/production", runtimeKv);
    vaultEso.applyExternalSecrets(esFiles);
    for (const name of ["registry-pull-secret", "repody-runtime-secrets", "repody-data-postgresql", "repody-data-redis", "repody-data-minio"]) {
      kube.kubectl(
        [
          "annotate",
          "externalsecret",
          name,
          "-n",
          NS.repody,
          "force-sync=" + new Date().toISOString(),
          "--overwrite",
        ],
        { quiet: true },
      );
    }
    vaultEso.waitExternalSecrets();
  }

  log("seed", `Vault seeded (${profile}); pull secrets synced`);
}

function registerGitOps() {
  kube.requireCluster();
  const hostList = hosts();
  const repo = imageRepo(hostList);
  promoteGitValues(hostList, repo);
  argocdLab.applyApplications(profile);
}

function deployHelm() {
  kube.requireCluster();
  ensureHelmDeps();

  const hostList = hosts();
  const repo = imageRepo(hostList);
  const rendered = writeRenderedValues(hostList, repo);

  deployDataPlane();

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
    { dryRun },
  );

  const backendImage = `${repo}/repody-backend:${tag}`;
  if (!dryRun) {
    ensureMigrationsJob({
      apply: kube.kubectl,
      getOut: kube.kubectlOut,
      fail,
      namespace: NS.repody,
      backendImage,
    });
  }

  const profileValues =
    profile === "external"
      ? "deploy/client/values-external.example.yaml"
      : "deploy/client/values-bundled.example.yaml";
  const labProfileValues =
    profile === "external"
      ? "deploy/client/lab/values.lab.external.yaml"
      : "deploy/client/lab/values.lab.bundled.yaml";

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
      profileValues,
      "-f",
      "deploy/client/values-enterprise.example.yaml",
      "-f",
      "deploy/values/openshift.yaml",
      "-f",
      "deploy/client/lab/values.lab.common.yaml",
      "-f",
      labProfileValues,
      "-f",
      rendered.outPath,
      "--wait",
      "--timeout",
      "30m",
    ],
    { dryRun },
  );

  log(
    "deploy",
    [
      `profile=${profile} registry=${registryMode} (direct helm)`,
      `  Web:   https://${hostList.web}`,
      `  API:   https://${hostList.api}`,
      `  Auth:  https://${hostList.auth}`,
    ].join("\n"),
  );
}

function deploy() {
  if (gitops) {
    registerGitOps();
    sync();
  } else {
    deployHelm();
  }
}

function sync() {
  const apps = argocdLab.appNames(profile);
  argocdLab.syncApps(apps);
  argocdLab.waitHealthy(apps);
}

function logs() {
  if (dryRun) {
    log("logs", "skipped (dry-run)");
    return;
  }
  verifyJsonLogs({ kubectlOut: kube.kubectlOut, fail, namespace: NS.repody });
  log("logs", "JSON structured logs verified on API + Web");
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
  log("vlm", `host llama-server on :8081 (${hostVlmUrl()})`);
}

async function verify() {
  kube.requireCluster();
  const hostList = hosts();
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const apiUrl = `https://${hostList.api}/v1/healthz/live`;
  const webUrl = `https://${hostList.web}`;

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
  log("verify", [`ok: ${apiUrl}`, `web: ${webUrl} (HTTP ${(webProbe.stdout ?? "").trim() || "?"})`].join("\n"));
}

function clientReadyCheck() {
  if (dryRun) return;
  const check = run(
    "node",
    [
      "deploy/scripts/check-openshift-client-ready.mjs",
      "--namespace",
      NS.repody,
      `--profile=${profile}`,
      `--registry=${registryMode}`,
    ],
    { quiet: true },
  );
  if (check.status !== 0) {
    console.error((check.stderr ?? check.stdout ?? "").trim());
    fail("client readiness check failed");
  }
  log("client-ready", "production-shaped checks passed");
}

async function e2e() {
  buildImages();
  pushImages();
  seed();
  if (gitops) {
    registerGitOps();
    sync();
  } else {
    deployHelm();
  }
  if (args.flags.has("--vlm")) startVlm();
  await verify();
  logs();
  clientReadyCheck();
}

async function all() {
  preflight();
  if (args.flags.has("--clean")) clean();
  infra();
  await e2e();
}

const handlers = {
  preflight,
  clean,
  infra,
  platform,
  harbor,
  observability,
  build: buildImages,
  push: pushImages,
  images: pushImages,
  seed,
  register: registerGitOps,
  sync,
  deploy,
  logs,
  verify,
  e2e,
  all,
  registry: configureRegistryForPush,
  argocd: () => argocdLab.install(),
  vlm: startVlm,
};

const handler = handlers[args.cmd];
if (process.argv.includes("--check")) {
  process.exit(0);
}
if (!handler) {
  console.error(`Unknown command: ${args.cmd ?? "(none)"}`);
  console.error(
    "Commands: preflight clean infra build push seed register sync deploy logs verify e2e all",
  );
  console.error(
    "Flags: --profile=bundled|external --registry=harbor|openshift --helm --clean --dry-run --skip-* --vlm",
  );
  process.exit(1);
}

Promise.resolve(handler()).catch((error) => {
  fail(error instanceof Error ? error.message : String(error));
});
