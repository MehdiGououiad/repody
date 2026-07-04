#!/usr/bin/env node
/**
 * Enterprise production lab — Harbor push + private GitOps (Gitea) + Argo CD sync.
 *
 *   node deploy/scripts/enterprise-gitops-lab.mjs <command>
 *
 * Commands: preflight | platform | harbor | gitea | gitops | images | argocd | sync | verify | all
 * Flags: --skip-images --skip-clean --use-existing-cluster
 *
 * Reuses k3d cluster from k3s:client (repody-client) unless --skip-clean recreates via k3s script.
 */
import { spawn, spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readPackageVersion, parseArgs, log, fail, sleep } from "./lib/cli.mjs";
import { createVaultEsoHelpers, dockerConfigJson } from "./lib/vault-eso.mjs";
import { buildLabVaultKvs } from "./lib/lab-seed.mjs";
import { createTlsSecret } from "./lib/lab-tls.mjs";
import { bundledAuthValuesYaml, bundledRepodyValuesYaml } from "./lib/bundled-values.mjs";
import { promoteK3dImagesToHarbor as runHarborPromoteJob } from "./lib/harbor-promote.mjs";
import { resolveExecutable } from "./runtime-env.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const k3sRuntime = path.join(root, "deploy/client/lab/.runtime-k3s");
const runtimeDir = path.join(root, ".runtime-enterprise");
const CLUSTER = process.env.REPODY_K3S_CLUSTER ?? "repody-client";
const DOMAIN = process.env.REPODY_CLIENT_DOMAIN ?? "repody.test";
const LB_HTTPS_PORT = process.env.REPODY_K3S_HTTPS_PORT ?? "8443";
const HARBOR_USER = "admin";
const HARBOR_PASS = process.env.REPODY_HARBOR_PASSWORD ?? "Harbor12345";
const HARBOR_NODE_PORT = process.env.REPODY_HARBOR_NODE_PORT ?? "30500";
const GITEA_NODE_PORT = process.env.REPODY_GITEA_LOCAL_PORT ?? "30300";
const GITEA_USER = "gitops";
const GITEA_PASS = process.env.REPODY_GITEA_PASSWORD ?? "GitOps12345";
const NS = { repody: "repody", harbor: "harbor", gitops: "gitops", argocd: "argocd", vault: "vault" };

const args = parseArgs(process.argv);
const tag = (process.env.REPODY_IMAGE_TAG ?? readPackageVersion(root)).trim();

function run(cmd, cmdArgs, { quiet = false, cwd = root, input, env } = {}) {
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

function runOut(cmd, cmdArgs, opts = {}) {
  return run(cmd, cmdArgs, { ...opts, quiet: true });
}

function k3d(cmdArgs, opts = {}) {
  return run(resolveExecutable("k3d"), cmdArgs, opts);
}

function kubeconfigPath() {
  const kubePath = path.join(k3sRuntime, "kubeconfig");
  if (!existsSync(kubePath)) fail("k3s kubeconfig missing — run: pnpm k3s:client cluster bootstrap seed");
  return kubePath;
}

function kubectl(cmdArgs, opts = {}) {
  return run(resolveExecutable("kubectl"), cmdArgs, {
    ...opts,
    env: { ...process.env, KUBECONFIG: kubeconfigPath() },
  });
}

function kubectlOut(cmdArgs) {
  const r = kubectl(cmdArgs, { quiet: true });
  return r.status === 0 ? (r.stdout ?? "").trim() : "";
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

function helm(cmdArgs, opts = {}) {
  return run(resolveExecutable("helm"), cmdArgs, {
    ...opts,
    env: { ...process.env, KUBECONFIG: kubeconfigPath() },
  });
}

function startPortForward(ns, service, localPort, remotePort) {
  const child = spawn(
    resolveExecutable("kubectl"),
    ["port-forward", "-n", ns, `svc/${service}`, `${localPort}:${remotePort}`],
    {
      detached: true,
      stdio: "ignore",
      env: { ...process.env, KUBECONFIG: kubeconfigPath() },
    },
  );
  child.unref();
  sleep(4000);
  return child;
}

function stopPortForward(child) {
  if (child && !child.killed) {
    try {
      child.kill();
    } catch {
      /* ignore */
    }
  }
}

function k3dRegistryPushHost() {
  return `localhost:${process.env.REPODY_K3S_REGISTRY_PORT ?? "5050"}`;
}

/** In-cluster promote target (pods resolve cluster DNS). */
function harborInClusterHost() {
  return "harbor-registry.harbor.svc.cluster.local:5000";
}

/** Node/kubelet pull host — NodePort on localhost (https://docs.k3s.io/installation/private-registry). */
function harborPullHost() {
  return `127.0.0.1:${HARBOR_NODE_PORT}`;
}

function harborImageRepo() {
  return `${harborPullHost()}/repody`;
}

function giteaInternalBase() {
  return `http://gitea-http.${NS.gitops}.svc.cluster.local:3000`;
}

function giteaExternalBase() {
  return `http://127.0.0.1:${GITEA_NODE_PORT}`;
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
  const checks = [
    ["docker", ["version"]],
    ["helm", ["version"]],
    ["kubectl", ["version", "--client"]],
    ["git", ["--version"]],
  ];
  for (const [tool, toolArgs] of checks) {
    if (runOut(resolveExecutable(tool), toolArgs).status !== 0) fail(`Missing: ${tool}`);
  }
  if (k3d(["version"], { quiet: true }).status !== 0) fail("Missing k3d");
  log("preflight", "ok: docker, k3d, kubectl, helm, git");
}

function k3sSubcommand(name) {
  const result = run(resolveExecutable("node"), ["deploy/scripts/k3s-client-bundled.mjs", name], { cwd: root });
  if (result.status !== 0) fail(`k3s-client-bundled.mjs ${name} failed`);
}

function platform() {
  mkdirSync(runtimeDir, { recursive: true });
  if (!args.flags.has("--use-existing-cluster")) {
    if (!args.flags.has("--skip-clean")) k3sSubcommand("clean");
    k3sSubcommand("cluster");
  } else {
    k3sSubcommand("cluster");
  }
  k3sSubcommand("bootstrap");
  k3sSubcommand("observability");
  log("platform", "k3d cluster + Vault + ESO + OTEL ready (secrets seeded after Harbor push)");
}

/** bcrypt htpasswd — required by registry:2 (https://distribution.github.io/distribution/about/deploying/) */
function htpasswdLine() {
  const r = runOut(resolveExecutable("docker"), [
    "run",
    "--rm",
    "--entrypoint",
    "htpasswd",
    "httpd:2",
    "-Bbn",
    HARBOR_USER,
    HARBOR_PASS,
  ], { quiet: true });
  if (r.status !== 0) {
    fail(`Harbor htpasswd (bcrypt) failed: ${r.stderr ?? ""}`);
  }
  return (r.stdout ?? "").trim();
}

function k3dNodeContainers() {
  const result = runOut(resolveExecutable("docker"), ["ps", "--filter", `name=k3d-${CLUSTER}`, "--format", "{{.Names}}"], {
    quiet: true,
  });
  return (result.stdout ?? "")
    .trim()
    .split(/\r?\n/)
    .filter((name) => /-(server|agent)-\d+$/.test(name));
}

/** HTTP mirror for Harbor NodePort — kubelet pulls on the node, not via cluster DNS. */
function configureK3sHarborRegistryMirror() {
  const pullHost = harborPullHost();
  const k3dReg = "k3d-repody-registry.localhost";
  const port = process.env.REPODY_K3S_REGISTRY_PORT ?? "5050";
  const registriesPath = path.join(runtimeDir, "k3s-registries.yaml");
  const content = `mirrors:
  ${k3dReg}:5000:
    endpoint:
      - http://${k3dReg}:5000
  ${k3dReg}:${port}:
    endpoint:
      - http://${k3dReg}:5000
  ${pullHost}:
    endpoint:
      - http://${pullHost}
configs: {}
auths: {}
`;
  mkdirSync(runtimeDir, { recursive: true });
  writeFileSync(registriesPath, content, "utf8");
  const nodes = k3dNodeContainers();
  if (nodes.length === 0) fail(`no k3d nodes found for cluster ${CLUSTER}`);
  for (const node of nodes) {
    const copy = run(resolveExecutable("docker"), ["cp", registriesPath, `${node}:/etc/rancher/k3s/registries.yaml`], {
      quiet: true,
    });
    if (copy.status !== 0) fail(`docker cp registries.yaml to ${node} failed`);
    const restart = run(resolveExecutable("docker"), ["restart", node], { quiet: true });
    if (restart.status !== 0) fail(`restart k3d node ${node} failed`);
  }
  sleep(15000);
  const ready = kubectl(["wait", "--for=condition=Ready", "node", "--all", "--timeout=180s"], { quiet: true });
  if (ready.status !== 0) fail("k3s nodes not ready after Harbor registry mirror update");
  const bootstrap = run(resolveExecutable("node"), ["deploy/scripts/k3s-client-bundled.mjs", "bootstrap"], { cwd: root });
  if (bootstrap.status !== 0) fail("Vault/ESO re-bootstrap after k3s node restart failed");
}

function harbor() {
  const manifestPath = path.join(runtimeDir, "harbor-registry.yaml");
  let raw = readFileSync(path.join(root, "deploy/client/lab/manifests/harbor-registry-lab.yaml"), "utf8");
  raw = raw.replace("admin:$2y$05$PLACEHOLDER", htpasswdLine());
  writeFileSync(manifestPath, raw, "utf8");
  kubectl(["apply", "-f", manifestPath]);
  kubectl(["rollout", "restart", "deploy/harbor-registry", "-n", NS.harbor], { quiet: true });
  const rollout = kubectl(
    ["rollout", "status", "deploy/harbor-registry", "-n", NS.harbor, "--timeout=180s"],
    { quiet: true },
  );
  if (rollout.status !== 0) fail("Harbor registry rollout failed");
  configureK3sHarborRegistryMirror();
  log(
    "harbor",
    [
      `Lab registry running (Harbor-compatible pull-secret contract).`,
      `Build push (host): ${k3dRegistryPushHost()}/repody/*`,
      `Harbor pull (kubelet): ${harborPullHost()}/repody/*`,
      `Login: ${HARBOR_USER} / ${HARBOR_PASS}`,
    ].join("\n"),
  );
}

function gitea() {
  helm(["repo", "add", "gitea-charts", "https://dl.gitea.com/charts/", "--force-update"], { quiet: true });
  helm(["repo", "update", "gitea-charts"], { quiet: true });
  kubectl(["create", "namespace", NS.gitops, "--dry-run=client", "-o", "yaml"], { quiet: true });
  kubectl(["apply", "-f", "-"], {
    input: `apiVersion: v1\nkind: Namespace\nmetadata:\n  name: ${NS.gitops}\n`,
    quiet: true,
  });
  helm(
    [
      "upgrade",
      "--install",
      "gitea",
      "gitea-charts/gitea",
      "-n",
      NS.gitops,
      "--set",
      "gitea.admin.username=" + GITEA_USER,
      "--set",
      "gitea.admin.password=" + GITEA_PASS,
      "--set",
      "gitea.admin.email=gitops@repody.local",
      "--set",
      "persistence.enabled=false",
      "--set",
      "service.http.type=NodePort",
      "--set",
      "service.http.nodePort=" + GITEA_NODE_PORT,
      "--set",
      "service.http.port=3000",
      "--wait",
      "--timeout",
      "10m",
    ],
    { quiet: false },
  );
  const deadline = Date.now() + 300_000;
  while (Date.now() < deadline) {
    const r = runOut(curlBin(), ["-fsS", `${giteaExternalBase()}/api/v1/version`], { quiet: true });
    if (r.status === 0) break;
    sleep(5000);
  }
  log("gitea", `Git server ready at ${giteaExternalBase()} (${GITEA_USER})`);
}

function curlBin() {
  return process.platform === "win32" ? "curl.exe" : "curl";
}

function ensureGiteaRepo(name) {
  const auth = `${GITEA_USER}:${GITEA_PASS}`;
  const exists = runOut(curlBin(), [
    "-s",
    "-o",
    process.platform === "win32" ? "NUL" : "/dev/null",
    "-w",
    "%{http_code}",
    "-u",
    auth,
    `${giteaExternalBase()}/api/v1/repos/${GITEA_USER}/${name}`,
  ], { quiet: true });
  if ((exists.stdout ?? "").trim() === "200") return;

  const create = runOut(curlBin(), [
    "-s",
    "-o",
    process.platform === "win32" ? "NUL" : "/dev/null",
    "-w",
    "%{http_code}",
    "-u",
    auth,
    "-X",
    "POST",
    `${giteaExternalBase()}/api/v1/user/repos`,
    "-H",
    "Content-Type: application/json",
    "-d",
    JSON.stringify({ name, private: true, auto_init: false, default_branch: "main" }),
  ], { quiet: true });
  const code = (create.stdout ?? "").trim();
  if (code !== "201" && code !== "409") {
    fail(`Gitea create repo ${name} failed (HTTP ${code}): ${create.stderr ?? ""}`);
  }
}

function k3dRegistryPromoteHost() {
  const name = "k3d-repody-registry.localhost";
  const network = `k3d-${CLUSTER}`;
  const result = runOut(resolveExecutable("docker"), [
    "inspect",
    "-f",
    `{{(index .NetworkSettings.Networks "${network}").IPAddress}}:5000`,
    name,
  ], { quiet: true });
  const host = (result.stdout ?? "").trim();
  if (result.status !== 0 || !host || host === ":5000") {
    fail(`resolve k3d registry on ${network} failed: ${result.stderr ?? ""}`);
  }
  return host;
}

function promoteK3dImagesToHarborInCluster() {
  runHarborPromoteJob({
    kubectl,
    kubectlOut,
    fail,
    sleep,
    runtimeDir,
    harborNamespace: NS.harbor,
    tag,
    sourceRegistryHost: k3dRegistryPromoteHost(),
    destRegistryHost: harborInClusterHost(),
    harborUser: HARBOR_USER,
    harborPass: HARBOR_PASS,
  });
}

/** Harbor HTTP registry — https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/ */
function pushImagesToHarbor() {
  process.env.REPODY_IMAGE_REGISTRY = `${k3dRegistryPushHost()}/repody`;
  process.env.REPODY_IMAGE_TAG = tag;
  const build = run(resolveExecutable("node"), ["deploy/scripts/build-images.mjs", "--push"], { cwd: root });
  if (build.status !== 0) fail("docker build/push to k3d registry failed");
  promoteK3dImagesToHarborInCluster();
}

function promoteK3dImagesToHarbor() {
  promoteK3dImagesToHarborInCluster();
}

function harborDockerConfig() {
  return dockerConfigJson(harborPullHost(), HARBOR_USER, HARBOR_PASS);
}

function seedVaultWithHarbor() {
  const { dataKv, runtimeKv } = buildLabVaultKvs({ dockerConfigJson: harborDockerConfig() });
  vaultEso.putVaultKv("secret/repody/production/data", dataKv);
  vaultEso.putVaultKv("secret/repody/production", runtimeKv);
  vaultEso.applyExternalSecrets(vaultEso.bundledExternalSecretFiles);
  vaultEso.waitExternalSecrets();
  log("seed", "Vault updated with Harbor pull secret; ExternalSecrets synced");
}


function images() {
  if (args.flags.has("--skip-images")) {
    promoteK3dImagesToHarbor();
  } else {
    pushImagesToHarbor();
  }
  seedVaultWithHarbor();
  log(
    "images",
    [
      `Harbor images at ${harborPullHost()}/repody/*:${tag}`,
      "Promoted in-cluster (skopeo) from k3d registry docker network",
    ].join("\n"),
  );
}

function gitRun(cwd, gitArgs) {
  const r = runOut(resolveExecutable("git"), gitArgs, { cwd, quiet: true });
  if (r.status !== 0) fail(`git ${gitArgs.join(" ")} failed: ${r.stderr ?? ""}`);
}

function writeClientGitopsValues(dir) {
  const hosts = clientHosts();
  const repo = harborImageRepo();
  const enterprise = readFileSync(path.join(root, "deploy/client/values-enterprise.example.yaml"), "utf8");
  writeFileSync(path.join(dir, "values.enterprise.yaml"), enterprise, "utf8");
  writeFileSync(
    path.join(dir, "values.k3s.yaml"),
    readFileSync(path.join(root, "deploy/values/k3s.yaml"), "utf8"),
    "utf8",
  );
  writeFileSync(
    path.join(dir, "values.data.yaml"),
    readFileSync(path.join(root, "deploy/client/bundled/values.data.yaml"), "utf8"),
    "utf8",
  );
  writeFileSync(
    path.join(dir, "values.auth.yaml"),
    bundledAuthValuesYaml({ authHost: hosts.auth, className: "traefik" }),
    "utf8",
  );
  writeFileSync(
    path.join(dir, "values.yaml"),
    bundledRepodyValuesYaml({
      imageRepo: repo,
      tag,
      hosts,
      vlmUrl: "http://127.0.0.1:65535/v1",
      ingressClassName: "traefik",
    }),
    "utf8",
  );
}

function pushRepo(localDir, remoteUrl) {
  gitRun(localDir, ["init", "-b", "main"]);
  gitRun(localDir, ["config", "user.email", "gitops@repody.local"]);
  gitRun(localDir, ["config", "user.name", "Repody GitOps Lab"]);
  gitRun(localDir, ["add", "."]);
  gitRun(localDir, ["commit", "-m", "enterprise lab gitops"]);
  const authUrl = remoteUrl.replace("http://", `http://${GITEA_USER}:${encodeURIComponent(GITEA_PASS)}@`);
  runOut(resolveExecutable("git"), ["remote", "remove", "origin"], { cwd: localDir, quiet: true });
  gitRun(localDir, ["remote", "add", "origin", authUrl]);
  const push = runOut(resolveExecutable("git"), ["push", "-u", "origin", "main", "--force"], {
    cwd: localDir,
    quiet: true,
  });
  if (push.status !== 0) fail(`git push to ${remoteUrl} failed: ${push.stderr}`);
}

function gitWorkDir() {
  const dir = path.join(os.tmpdir(), "repody-enterprise-lab", "git");
  mkdirSync(dir, { recursive: true });
  return dir;
}

function gitops() {
  const base = gitWorkDir();
  const vendorDir = path.join(base, "repody-vendor");
  const clientDir = path.join(base, "repody-client");
  rmSync(vendorDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 500 });
  rmSync(clientDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 500 });
  mkdirSync(vendorDir, { recursive: true });
  mkdirSync(clientDir, { recursive: true });

  const helmDeps = run(resolveExecutable("node"), ["scripts/helm-deps.mjs", "--update"], { cwd: root, quiet: true });
  if (helmDeps.status !== 0) fail("helm dependency update failed for vendor charts");
  const helmDst = path.join(vendorDir, "deploy/helm");
  mkdirSync(path.dirname(helmDst), { recursive: true });
  cpSync(path.join(root, "deploy/helm"), helmDst, { recursive: true });
  writeClientGitopsValues(clientDir);

  const pf = startPortForward(NS.gitops, "gitea-http", GITEA_NODE_PORT, 3000);
  try {
    ensureGiteaRepo("repody-vendor");
    ensureGiteaRepo("repody-client");

    const vendorRemote = `${giteaExternalBase()}/${GITEA_USER}/repody-vendor.git`;
    const clientRemote = `${giteaExternalBase()}/${GITEA_USER}/repody-client.git`;
    pushRepo(vendorDir, vendorRemote);
    pushRepo(clientDir, clientRemote);
  } finally {
    stopPortForward(pf);
  }

  const meta = {
    vendorRepoUrl: `${giteaInternalBase()}/${GITEA_USER}/repody-vendor.git`,
    clientRepoUrl: `${giteaInternalBase()}/${GITEA_USER}/repody-client.git`,
    vendorRevision: "main",
  };
  writeFileSync(path.join(runtimeDir, "gitops-meta.json"), JSON.stringify(meta, null, 2), "utf8");
  log("gitops", `vendor + client repos pushed to Gitea\n${JSON.stringify(meta, null, 2)}`);
}

function argocd() {
  helm(["repo", "add", "argo", "https://argoproj.github.io/argo-helm", "--force-update"], { quiet: true });
  helm(["repo", "update", "argo"], { quiet: true });
  kubectl(["create", "namespace", NS.argocd, "--dry-run=client", "-o", "yaml"], { quiet: true });
  kubectl(["apply", "-f", "-"], {
    input: `apiVersion: v1\nkind: Namespace\nmetadata:\n  name: ${NS.argocd}\n`,
    quiet: true,
  });
  helm(
    [
      "upgrade",
      "--install",
      "argocd",
      "argo/argo-cd",
      "-n",
      NS.argocd,
      "--set",
      "configs.params.server\\.insecure=true",
      "--wait",
      "--timeout",
      "10m",
    ],
    { quiet: false },
  );

  const meta = JSON.parse(readFileSync(path.join(runtimeDir, "gitops-meta.json"), "utf8"));
  const repoSecret = `apiVersion: v1
kind: Secret
metadata:
  name: gitea-repos
  namespace: ${NS.argocd}
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: ${meta.vendorRepoUrl}
  username: ${GITEA_USER}
  password: ${GITEA_PASS}
---
apiVersion: v1
kind: Secret
metadata:
  name: gitea-client-gitops
  namespace: ${NS.argocd}
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: ${meta.clientRepoUrl}
  username: ${GITEA_USER}
  password: ${GITEA_PASS}
`;
  kubectl(["apply", "-f", "-"], { input: repoSecret, quiet: true });

  kubectl(["delete", "application", "repody", "repody-auth", "repody-data", "-n", NS.argocd, "--ignore-not-found"], {
    quiet: true,
  });
  helm(["uninstall", "repody", "-n", NS.repody], { quiet: true });
  helm(["uninstall", "repody-auth", "-n", NS.repody], { quiet: true });
  helm(["uninstall", "repody-data", "-n", NS.repody], { quiet: true });
  kubectl(["delete", "job", "repody-migrations-manual", "-n", NS.repody, "--ignore-not-found"], { quiet: true });

  let apps = readFileSync(path.join(root, "deploy/client/lab/argocd/applications.yaml"), "utf8");
  apps = apps
    .replaceAll("VENDOR_REPO_URL", meta.vendorRepoUrl)
    .replaceAll("CLIENT_REPO_URL", meta.clientRepoUrl)
    .replaceAll("VENDOR_REVISION", meta.vendorRevision);
  const appsPath = path.join(runtimeDir, "argocd-applications.yaml");
  writeFileSync(appsPath, apps, "utf8");
  kubectl(["apply", "-f", appsPath]);

  createLabTlsSecret();
  log("argocd", "Argo CD installed; Applications repody-data → repody-auth → repody applied");
}

function createLabTlsSecret() {
  const hosts = clientHosts();
  createTlsSecret({
    apply: kubectl,
    run: runOut,
    runtimeDir,
    domain: DOMAIN,
    sanHosts: [hosts.web, hosts.api, hosts.auth, hosts.files],
    namespace: NS.repody,
    fail,
  });
}

function triggerArgoSync() {
  const patchPath = path.join(runtimeDir, "argocd-sync-patch.json");
  writeFileSync(
    patchPath,
    JSON.stringify({
      operation: {
        initiatedBy: { username: "enterprise-lab" },
        sync: { prune: true, syncStrategy: { apply: { force: true } } },
      },
    }),
    "utf8",
  );
  for (const name of ["repody-data", "repody-auth", "repody"]) {
    kubectl(["annotate", "application", name, "-n", NS.argocd, "argocd.argoproj.io/refresh=hard", "--overwrite"], {
      quiet: true,
    });
    kubectl(["patch", "application", name, "-n", NS.argocd, "--type", "merge", "--patch-file", patchPath], {
      quiet: true,
    });
  }
  sleep(10000);
}

function sync() {
  triggerArgoSync();
  const deadline = Date.now() + 900_000;
  const apps = ["repody-data", "repody-auth", "repody"];
  while (Date.now() < deadline) {
    const statuses = apps.map((name) => {
      const health = kubectlOut([
        "get",
        "application",
        name,
        "-n",
        NS.argocd,
        "-o",
        "jsonpath={.status.health.status}",
      ]);
      const sync = kubectlOut([
        "get",
        "application",
        name,
        "-n",
        NS.argocd,
        "-o",
        "jsonpath={.status.sync.status}",
      ]);
      return `${name}:${sync}/${health}`;
    });
    console.log(statuses.join(" | "));
    const allHealthy = apps.every((name) => {
      const health = kubectlOut([
        "get",
        "application",
        name,
        "-n",
        NS.argocd,
        "-o",
        "jsonpath={.status.health.status}",
      ]);
      const sync = kubectlOut([
        "get",
        "application",
        name,
        "-n",
        NS.argocd,
        "-o",
        "jsonpath={.status.sync.status}",
      ]);
      return health === "Healthy" && sync === "Synced";
    });
    if (allHealthy) {
      log("sync", "All Argo CD Applications synced and healthy");
      return;
    }
    sleep(15000);
  }
  kubectl(["get", "applications", "-n", NS.argocd]);
  kubectl(["get", "pods", "-n", NS.repody]);
  fail("Argo CD sync did not reach Healthy/Synced within timeout");
}

function verify() {
  const hosts = clientHosts();
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const apiUrl = `https://${hosts.api}:${LB_HTTPS_PORT}/v1/healthz/live`;
  const resolve = ["--resolve", `${hosts.api}:${LB_HTTPS_PORT}:127.0.0.1`];
  let ok = false;
  for (let i = 0; i < 24; i++) {
    if (runOut(curl, [...resolve, "-kfsS", "--max-time", "8", apiUrl], { quiet: true }).status === 0) {
      ok = true;
      break;
    }
    sleep(5000);
  }
  if (!ok) fail(`API health failed: ${apiUrl}`);

  for (const app of ["repody-data", "repody-auth", "repody"]) {
    const health = kubectlOut(["get", "application", app, "-n", NS.argocd, "-o", "jsonpath={.status.health.status}"]);
    const sync = kubectlOut(["get", "application", app, "-n", NS.argocd, "-o", "jsonpath={.status.sync.status}"]);
    if (health !== "Healthy" || sync !== "Synced") {
      fail(`Argo CD Application ${app} is ${sync}/${health} — expected Synced/Healthy`);
    }
  }

  log(
    "verify",
    [
      "Enterprise GitOps lab healthy.",
      `Harbor: ${harborPullHost()}/repody`,
      `Argo CD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443`,
      `API: ${apiUrl}`,
    ].join("\n"),
  );
}

const steps = {
  preflight,
  platform,
  harbor,
  gitea,
  gitops,
  images,
  argocd,
  sync,
  verify,
  all: async () => {
    preflight();
    platform();
    harbor();
    gitea();
    gitops();
    images();
    argocd();
    sync();
    verify();
  },
};

if (args.flags.has("--use-existing-cluster")) {
  const orig = steps.platform;
  steps.platform = () => {
    mkdirSync(runtimeDir, { recursive: true });
    k3sSubcommand("cluster");
    if (!kubectlOut(["get", "ns", NS.vault])) k3sSubcommand("bootstrap");
    else log("platform", "reusing Vault + ESO from existing cluster");
    k3sSubcommand("observability");
  };
}

const step = steps[args.cmd];
if (!step) fail(`unknown command: ${args.cmd}`);
Promise.resolve(step()).catch((err) => fail(err?.message ?? String(err)));
