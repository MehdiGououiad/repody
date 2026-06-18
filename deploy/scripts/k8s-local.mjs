#!/usr/bin/env node
/**
 * Local Kubernetes prod-path smoke test: kind + Envoy Gateway + Argo CD + Helm.
 *
 *   pnpm k8s:local up     Create cluster, deploy Repody, register Argo CD app
 *   pnpm k8s:local down   Delete the kind cluster
 *   pnpm k8s:local status Show pods / gateway / Argo CD app health
 */
import { spawn, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const CLUSTER = "repody-local";
const NS = "repody";
const ENVOY_NS = "envoy-gateway-system";
const ARGO_NS = "argocd";
const ENVOY_CHART = "oci://docker.io/envoyproxy/gateway-helm";
const ENVOY_VERSION = "v1.4.0";
const ARGO_INSTALL_URL =
  "https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml";

const LOCAL_HOSTS = [
  "app.repody.local",
  "api.repody.local",
  "files.repody.local",
  "auth.repody.local",
];
const KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.6.3";
const LOCAL_REGISTRY = "localhost:5001";
const REGISTRY_NAME = "kind-registry";
const KIND_PLATFORM =
  process.arch === "arm64" ? "linux/arm64" : "linux/amd64";
const CHART_DIR = path.join(root, "deploy/helm/repody");
const VALUES_LOCAL = path.join(CHART_DIR, "values-local.yaml");
const VALUES_BASE = path.join(CHART_DIR, "values.yaml");

/** @param {string} cmd @param {string[]} args @param {Record<string, string | undefined>} [extraEnv] */
function run(cmd, args, extraEnv = {}) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    cwd: root,
    env: { ...process.env, ...extraEnv },
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

/** @param {string} cmd @param {string[]} args */
function capture(cmd, args) {
  const result = spawnSync(cmd, args, {
    encoding: "utf8",
    cwd: root,
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || `${cmd} failed`);
  }
  return (result.stdout ?? "").trim();
}

function heading(text) {
  console.error(`\n▶ ${text}\n`);
}

function sleep(ms) {
  if (process.platform === "win32") {
    spawnSync("powershell", ["-Command", `Start-Sleep -Milliseconds ${ms}`], {
      stdio: "ignore",
    });
  } else {
    spawnSync("sleep", [String(Math.ceil(ms / 1000))], { stdio: "ignore" });
  }
}

function waitFor(condition, label, timeoutMs = 600_000, intervalMs = 5_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (condition()) {
      console.error(`✓ ${label}`);
      return;
    }
    console.error(`… waiting for ${label}`);
    sleep(intervalMs);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

function resolveImageTag() {
  try {
    return capture("git", ["rev-parse", "--short=12", "HEAD"]);
  } catch {
    return "latest";
  }
}

/** @param {string[]} extraHelmSets */
function collectHelmImages(extraHelmSets = []) {
  const args = [
    "template",
    "repody",
    CHART_DIR,
    "-f",
    VALUES_BASE,
    "-f",
    VALUES_LOCAL,
    "--set",
    "global.imageRegistry=",
    ...extraHelmSets,
  ];
  const rendered = capture("helm", args);
  const images = new Set();
  for (const line of rendered.split("\n")) {
    const match = line.match(/^\s*image:\s*["']?([^"'\s]+)["']?\s*$/);
    if (match) {
      images.add(
        match[1]
          .replace(/^docker\.io\//, "")
          .replace(/^registry-1\.docker\.io\//, ""),
      );
    }
  }
  return [...images];
}

function normalizeImageRef(image) {
  return image
    .replace(/^docker\.io\//, "")
    .replace(/^registry-1\.docker\.io\//, "");
}

function localRegistryRef(image) {
  return `${LOCAL_REGISTRY}/${normalizeImageRef(image)}`;
}

function ensureLocalRegistry() {
  heading(`Starting local registry (${LOCAL_REGISTRY} — Harbor-equivalent for kind)`);
  const inspect = spawnSync(
    "docker",
    ["inspect", "-f", "{{.State.Running}}", REGISTRY_NAME],
    { encoding: "utf8", shell: process.platform === "win32" },
  );
  if (inspect.stdout?.trim() === "true") {
    console.error(`✓ ${REGISTRY_NAME} already running`);
    return;
  }
  spawnSync("docker", ["rm", "-f", REGISTRY_NAME], {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  run("docker", [
    "run",
    "-d",
    "--restart=always",
    "-p",
    `127.0.0.1:5001:5000`,
    "--name",
    REGISTRY_NAME,
    "registry:2",
  ]);
}

function connectRegistryToKind() {
  const result = spawnSync(
    "docker",
    ["network", "connect", "kind", REGISTRY_NAME],
    { encoding: "utf8", shell: process.platform === "win32" },
  );
  if (result.status === 0) {
    console.error(`✓ ${REGISTRY_NAME} attached to kind network`);
    return;
  }
  const stderr = result.stderr ?? "";
  if (stderr.includes("already exists")) {
    console.error(`✓ ${REGISTRY_NAME} already on kind network`);
    return;
  }
  if (stderr) console.error(stderr.trim());
}

/** Push to local registry — same workflow clients use with Harbor/GHCR. */
function pushToLocalRegistry(image, { localBuild = false } = {}) {
  const upstream = normalizeImageRef(image);
  if (localBuild) {
    const inspect = spawnSync(
      "docker",
      ["image", "inspect", upstream],
      { stdio: "ignore", shell: process.platform === "win32" },
    );
    if (inspect.status !== 0) {
      throw new Error(`Local image missing: ${upstream} (build step must run first)`);
    }
  } else {
    console.error(`→ pull ${upstream} (${KIND_PLATFORM})`);
    run("docker", ["pull", "--platform", KIND_PLATFORM, upstream]);
  }
  const dest = localRegistryRef(upstream);
  run("docker", ["tag", upstream, dest]);
  console.error(`→ push ${dest}`);
  run("docker", ["push", dest]);
  return dest;
}

/** @param {string} imageTag */
function buildRegistryHelmSets(imageTag) {
  return [
    "--set",
    `global.imageRegistry=${LOCAL_REGISTRY}`,
    "--set",
    "global.security.allowInsecureImages=true",
    "--set",
    `images.api.repository=${LOCAL_REGISTRY}/repody-api`,
    "--set",
    `images.worker.repository=${LOCAL_REGISTRY}/repody-worker`,
    "--set",
    `images.web.repository=${LOCAL_REGISTRY}/repody-web`,
    "--set",
    `images.api.tag=${imageTag}`,
    "--set",
    `images.worker.tag=${imageTag}`,
    "--set",
    `images.web.tag=${imageTag}`,
    "--set",
    "images.api.pullPolicy=IfNotPresent",
    "--set",
    "images.worker.pullPolicy=IfNotPresent",
    "--set",
    "images.web.pullPolicy=IfNotPresent",
    "--set",
    `hatchet.postgresImage=${localRegistryRef("postgres:17.10-alpine")}`,
    "--set",
    `hatchet.waitInitImage=${localRegistryRef("busybox:1.37.0")}`,
    "--set",
    `hatchet.kubectlImage=${localRegistryRef("dtzar/helm-kubectl:3.18.6")}`,
    "--set",
    `hatchet.image=${localRegistryRef("ghcr.io/hatchet-dev/hatchet/hatchet-lite:latest")}`,
    "--set",
    `hatchet.adminImage=${localRegistryRef("ghcr.io/hatchet-dev/hatchet/hatchet-admin:latest")}`,
    "--set",
    `keycloak.image=${localRegistryRef(KEYCLOAK_IMAGE)}`,
  ];
}

function repodyPodsReady() {
  try {
    const phases = capture("kubectl", [
      "-n",
      NS,
      "get",
      "pods",
      "-o",
      "jsonpath={range .items[*]}{.status.phase}{' '}{end}",
    ]);
    const list = phases.trim().split(/\s+/).filter(Boolean);
    if (list.length === 0) return false;
    return list.every((phase) => phase === "Running" || phase === "Succeeded");
  } catch {
    return false;
  }
}

function gatewayProgrammed() {
  try {
    const listener = capture("kubectl", [
      "-n",
      NS,
      "get",
      "gateway/repody",
      "-o",
      "jsonpath={.status.listeners[0].conditions[?(@.type=='Programmed')].status}",
    ]);
    return listener === "True";
  } catch {
    return false;
  }
}

function envoyGatewayServiceName() {
  return capture("kubectl", [
    "-n",
    ENVOY_NS,
    "get",
    "svc",
    "-l",
    "gateway.envoyproxy.io/owning-gateway-name=repody,gateway.envoyproxy.io/owning-gateway-namespace=repody",
    "-o",
    "jsonpath={.items[0].metadata.name}",
  ]);
}

function ensureWebAuthHostAlias() {
  if (!envoyGatewayServiceName()) return;
  const svc = envoyGatewayServiceName();
  const envoyIp = capture("kubectl", [
    "-n",
    ENVOY_NS,
    "get",
    `svc/${svc}`,
    "-o",
    "jsonpath={.spec.clusterIP}",
  ]);
  if (!envoyIp) return;
  console.error(`→ web hostAlias ${envoyIp} → auth.repody.local`);
  run("helm", [
    "upgrade",
    "repody",
    CHART_DIR,
    "-n",
    NS,
    "--reuse-values",
    "--set",
    `gatewayApi.authHostAliasIp=${envoyIp}`,
    "--timeout",
    "10m",
  ]);
}

function ensureEnvoyNodePort() {
  if (!envoyGatewayServiceName()) return;
  const svc = envoyGatewayServiceName();
  const nodePort = capture("kubectl", [
    "-n",
    ENVOY_NS,
    "get",
    `svc/${svc}`,
    "-o",
    "jsonpath={.spec.ports[0].nodePort}",
  ]);
  if (nodePort === "30080") {
    console.error("✓ Envoy Gateway NodePort 30080");
    return;
  }
  console.error(`→ patch ${svc} to NodePort 30080`);
  run("kubectl", [
    "patch",
    "svc",
    svc,
    "-n",
    ENVOY_NS,
    "--type=json",
    "-p",
    '[{"op":"replace","path":"/spec/type","value":"NodePort"},{"op":"replace","path":"/spec/ports/0/nodePort","value":30080}]',
  ]);
}

const HOSTS_LINE = `127.0.0.1 ${LOCAL_HOSTS.join(" ")}`;

function hostsFilePath() {
  return process.platform === "win32"
    ? "C:\\Windows\\System32\\drivers\\etc\\hosts"
    : "/etc/hosts";
}

function missingLocalHosts() {
  let hostsText = "";
  try {
    hostsText = readFileSync(hostsFilePath(), "utf8");
  } catch {
    return [...LOCAL_HOSTS];
  }
  return LOCAL_HOSTS.filter((host) => !hostsText.includes(host));
}

function ensureHostsHint() {
  const missing = missingLocalHosts();
  if (missing.length === 0) return;
  const hostsPath = hostsFilePath();
  console.error("\n⚠ Hosts file missing Repody entries — browser cannot resolve *.repody.local");
  console.error(`  Run: pnpm k8s:local:hosts`);
  console.error(`  Or add to ${hostsPath} (admin):`);
  console.error(`  ${HOSTS_LINE}`);
  console.error("");
}

function cmdHosts() {
  const hostsPath = hostsFilePath();
  const missing = missingLocalHosts();
  if (missing.length === 0) {
    console.error(`✓ Hosts file already has Repody entries (${hostsPath})`);
    return;
  }
  console.error(`Missing: ${missing.join(", ")}`);
  console.error(`\nAdd this line to ${hostsPath}:\n\n  ${HOSTS_LINE}\n`);
  if (process.platform === "win32") {
    const ps = [
      `$line = '${HOSTS_LINE}'`,
      `$path = '${hostsPath.replace(/\\/g, "\\\\")}'`,
      `if (-not (Select-String -Path $path -Pattern 'app.repody.local' -Quiet)) { Add-Content -Path $path -Value $line }`,
      `Write-Host 'Done. Repody hosts entries added.'`,
    ].join("; ");
    console.error("Opening elevated PowerShell to update hosts (approve UAC)…\n");
    run("powershell", [
      "-NoProfile",
      "-Command",
      `Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command','${ps.replace(/'/g, "''")}'`,
    ]);
    return;
  }
  console.error(`On Linux/macOS, run with sudo:\n  echo '${HOSTS_LINE}' | sudo tee -a ${hostsPath}`);
}

function cmdDown() {
  heading(`Deleting kind cluster ${CLUSTER}`);
  run("kind", ["delete", "cluster", "--name", CLUSTER]);
  console.error("\n✓ kind cluster removed.\n");
}

function cmdStatus() {
  run("kubectl", ["config", "use-context", `kind-${CLUSTER}`]);
  run("kubectl", ["get", "nodes"]);
  run("kubectl", ["-n", NS, "get", "pods"]);
  run("kubectl", ["-n", NS, "get", "gateway,httproute"]);
  try {
    run("kubectl", ["-n", ARGO_NS, "get", "applications.argoproj.io"]);
  } catch {
    console.error("(Argo CD not installed)");
  }
}

function cmdUp() {
  const dockerCheck = spawnSync("docker", ["info"], {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  if (dockerCheck.status !== 0) {
    console.error(
      "\n✗ Docker is not running. Start Docker Desktop, then run: pnpm k8s:local\n",
    );
    process.exit(1);
  }

  heading("Stopping Compose stacks (free ports 80/443/8000/3000)");
  run("node", ["deploy/scripts/compose.mjs", "recipe", "stop"]);

  ensureLocalRegistry();

  heading(`Creating kind cluster ${CLUSTER}`);
  const kindConfig = path.join(root, "deploy/k8s/kind-repody-local.yaml");
  const existing = capture("kind", ["get", "clusters"]);
  if (existing.split("\n").includes(CLUSTER)) {
    run("kind", ["delete", "cluster", "--name", CLUSTER]);
  }
  run("kind", ["create", "cluster", "--config", kindConfig]);
  run("kubectl", ["config", "use-context", `kind-${CLUSTER}`]);
  run("kubectl", ["cluster-info"]);
  connectRegistryToKind();

  heading("Installing Envoy Gateway (Gateway API controller)");
  run("helm", [
    "upgrade",
    "--install",
    "eg",
    ENVOY_CHART,
    "--version",
    ENVOY_VERSION,
    "-n",
    ENVOY_NS,
    "--create-namespace",
    "--timeout",
    "10m",
  ]);
  waitFor(
    () => {
      try {
        const phase = capture("kubectl", [
          "-n",
          ENVOY_NS,
          "get",
          "pod",
          "-l",
          "app.kubernetes.io/name=gateway-helm",
          "-o",
          "jsonpath={.items[0].status.conditions[?(@.type=='Ready')].status}",
        ]);
        return phase === "True";
      } catch {
        return false;
      }
    },
    "Envoy Gateway controller",
    300_000,
  );

  heading("Installing Argo CD");
  run("kubectl", ["create", "namespace", ARGO_NS, "--dry-run=client", "-o", "yaml"]);
  run("kubectl", ["create", "namespace", ARGO_NS]);
  run("kubectl", [
    "apply",
    "-n",
    ARGO_NS,
    "--server-side",
    "--force-conflicts",
    "-f",
    ARGO_INSTALL_URL,
  ]);
  waitFor(
    () => {
      try {
        const ready = capture("kubectl", [
          "-n",
          ARGO_NS,
          "get",
          "deploy/argocd-server",
          "-o",
          "jsonpath={.status.readyReplicas}",
        ]);
        return ready === "1";
      } catch {
        return false;
      }
    },
    "Argo CD server",
    600_000,
  );

  heading("Preparing Repody VLM in Docker Model Runner");
  run("node", ["scripts/prepare-repody-vlm-model.mjs"]);

  heading("Preparing Helm chart dependencies");
  run("node", ["scripts/helm-deps.mjs"]);

  const imageTag = resolveImageTag();
  const tagHelmSets = [
    "--set",
    `images.api.tag=${imageTag}`,
    "--set",
    `images.worker.tag=${imageTag}`,
    "--set",
    `images.web.tag=${imageTag}`,
  ];

  heading(`Building Repody images (immutable tag ${imageTag})`);
  const buildEnv = {
    AUTH_KEYCLOAK_ISSUER: "http://auth.repody.local/realms/repody",
    AUDIT_OIDC_ISSUER: "http://auth.repody.local/realms/repody",
    AUDIT_MINIO_PUBLIC_ENDPOINT: "files.repody.local",
    REPODY_IMAGE_TAG: imageTag,
  };
  run("node", ["deploy/scripts/build-images.mjs"], buildEnv);

  heading("Publishing images to local registry (client Harbor workflow)");
  const helmImages = collectHelmImages(tagHelmSets);
  const toPublish = [
    ...new Set([
      ...helmImages,
      `repody-api:${imageTag}`,
      `repody-worker:${imageTag}`,
      `repody-web:${imageTag}`,
      KEYCLOAK_IMAGE,
    ]),
  ];
  console.error(`Images to publish: ${toPublish.length}`);
  for (const image of toPublish) {
    const localBuild =
      image.startsWith("repody-api:") ||
      image.startsWith("repody-worker:") ||
      image.startsWith("repody-web:");
    pushToLocalRegistry(image, { localBuild });
  }
  const registryHelmSets = buildRegistryHelmSets(imageTag);

  heading("Preparing namespace and Gateway edge");
  run("kubectl", ["create", "namespace", NS, "--dry-run=client", "-o", "yaml"]);
  run("kubectl", ["create", "namespace", NS]);
  run("kubectl", [
    "apply",
    "-f",
    path.join(root, "deploy/k8s/envoy-proxy-kind-nodeport.yaml"),
  ]);

  heading("Installing Repody Helm chart (Gateway API edge + in-cluster Keycloak)");
  run("helm", [
    "upgrade",
    "--install",
    "repody",
    CHART_DIR,
    "-n",
    NS,
    "-f",
    VALUES_BASE,
    "-f",
    VALUES_LOCAL,
    ...registryHelmSets,
    "--timeout",
    "25m",
  ]);

  heading("Registering Argo CD Application (manual sync until Git matches)");
  run("kubectl", ["apply", "-n", ARGO_NS, "-f", path.join(root, "deploy/argocd/repody-project.yaml")]);
  run("kubectl", [
    "apply",
    "-n",
    ARGO_NS,
    "-f",
    path.join(root, "deploy/argocd/repody-local.application.yaml"),
  ]);

  waitFor(() => repodyPodsReady(), "all Repody namespace pods ready", 1_500_000);
  waitFor(() => gatewayProgrammed(), "Gateway API programmed", 300_000);

  heading("Verifying API health via Gateway");
  ensureEnvoyNodePort();
  ensureWebAuthHostAlias();
  sleep(5_000);
  waitFor(
    () => {
      try {
        const body = capture("curl", [
          "-sf",
          "--max-time",
          "5",
          "-H",
          "Host: api.repody.local",
          "http://127.0.0.1/v1/healthz/live",
        ]);
        return body.includes('"status":"ok"') || body.includes('"status": "ok"');
      } catch {
        return false;
      }
    },
    "API health via Gateway (http://api.repody.local)",
    300_000,
  );

  let argoPassword = "(run: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d)";
  try {
    const b64 = capture("kubectl", [
      "-n",
      ARGO_NS,
      "get",
      "secret",
      "argocd-initial-admin-secret",
      "-o",
      "jsonpath={.data.password}",
    ]);
    if (b64) {
      argoPassword = Buffer.from(b64, "base64").toString("utf8");
    }
  } catch {
    // optional
  }

  ensureHostsHint();

  console.error(`
══════════════════════════════════════════════════════════════════════
 Local Kubernetes prod path is up (kind + Envoy Gateway + Argo CD)
──────────────────────────────────────────────────────────────────────
 Web (Gateway)     http://app.repody.local
 API (Gateway)     http://api.repody.local/v1/healthz/live
 Files (Gateway)   http://files.repody.local
 Keycloak (GW)     http://auth.repody.local
 (Requires hosts file + kind maps host :80 → NodePort 30080. Cloud clusters use LB :80.)
 Argo CD UI        kubectl port-forward svc/argocd-server -n argocd 8080:443
                   https://localhost:8080  (admin / ${argoPassword})
──────────────────────────────────────────────────────────────────────
 Registry:      ${LOCAL_REGISTRY} (local Harbor equivalent)
 Image tag:     ${imageTag} (git SHA)
 Sign in: operator@repody.local / repody-dev
 Argo CD app: repody-local (sync manually after git push, or argocd app sync --local)
 Tear down:   pnpm k8s:local down
══════════════════════════════════════════════════════════════════════
`);
}

const sub = process.argv[2] ?? "up";
if (sub === "up") cmdUp();
else if (sub === "down") cmdDown();
else if (sub === "status") cmdStatus();
else if (sub === "hosts") cmdHosts();
else {
  console.error("Usage: pnpm k8s:local [up|down|status|hosts]");
  process.exit(1);
}
