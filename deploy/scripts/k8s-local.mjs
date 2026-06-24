#!/usr/bin/env node
/**
 * Local Kubernetes prod-path smoke test: kind + Envoy Gateway + Argo CD + Helm.
 *
 *   pnpm k8s:local up     Create/reuse cluster, deploy Repody, register Argo CD app
 *   pnpm k8s:local up --with=obs
 *                         Also install Grafana/Loki/Tempo/Bugsink (off by default)
 *   pnpm k8s:local up --reset
 *                         Recreate the cluster from scratch
 *   pnpm stop             Uninstall Repody Helm release (keeps kind + Harbor)
 *   pnpm stop --cluster   Delete kind cluster (Harbor keeps running)
 *   pnpm dev              Bootstrap stack once; use pnpm dev:sync for daily code changes
 *   pnpm k8s:local down   Same as pnpm stop
 *   pnpm k8s:local status Show pods / gateway / Argo CD app health
 */
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  LOCAL_CREDENTIALS,
  LOCAL_HOSTS,
  localUrl,
  readPinnedImages,
  requirePinnedImage,
} from "./k8s-local-common.mjs";
import { createArgoCommands } from "./k8s-local-argo.mjs";
import { ARGO_INSTALL_URL } from "./argocd-local.mjs";
import { createGatewayCommands } from "./k8s-local-gateway.mjs";
import { createLocalHelmCommands } from "./k8s-local-helm.mjs";
import { createHostsCommands } from "./k8s-local-hosts.mjs";
import {
  createProcessAdapter,
  hasFlag,
  heading,
  requireDockerEngine,
  truthyEnv,
  waitFor,
  waitForWithProgress,
  traceSummary,
} from "./k8s-local-process.mjs";
import { createLocalRegistryCommands } from "./k8s-local-registry.mjs";
import { ensureGatewayPortsFree } from "./k8s-local-ports.mjs";
import { createLogCommands } from "./k8s-local-logs.mjs";
import { resolveLocalImageTags } from "./k8s-local-image-tag.mjs";
import { gitShortSha } from "./git-sha.mjs";
import {
  bumpHelmImageTags,
  readHelmImageTag,
} from "./bump-helm-image-tags.mjs";
import { resolveLocalRegistryConfig } from "./k8s-local-registry-config.mjs";
import { connectHarborToKind } from "./harbor-local.mjs";
import { createGitOpsHandoffCommands } from "./k8s-local-gitops.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const REGISTRY_CONFIG = resolveLocalRegistryConfig(root);
const PINNED_IMAGES = readPinnedImages(root);
const CLUSTER = "repody-local";
const NS_APP = "repody-app";
const NS_DATA = "repody-data";
const NS_QUEUE = "repody-queue";
const NS_AUTH = "repody-auth";
const LOCAL_NAMESPACES = [NS_DATA, NS_QUEUE, NS_AUTH, NS_APP];
const NS = NS_APP;
const ENVOY_NS = "envoy-gateway-system";
const ARGO_NS = "argocd";
const ARGO_REPO_URL = "https://github.com/MehdiGououiad/repody.git";
const ENVOY_CHART = "oci://docker.io/envoyproxy/gateway-helm";
const ENVOY_VERSION = "v1.4.0";
const LOCAL_ARGO_ROOT = path.join(root, "deploy/argocd/repody-local-root.application.yaml");

const KEYCLOAK_IMAGE = requirePinnedImage(PINNED_IMAGES, "REPODY_KEYCLOAK_IMAGE");
const LOCAL_REGISTRY = REGISTRY_CONFIG.localRegistry;
const KIND_CONFIG = REGISTRY_CONFIG.kindConfigFile;
const KIND_PLATFORM =
  process.arch === "arm64" ? "linux/arm64" : "linux/amd64";
const CHART_DIR = path.join(root, "deploy/helm/repody");
const CHART_DATA = path.join(root, "deploy/helm/repody-data");
const CHART_QUEUE = path.join(root, "deploy/helm/repody-queue");
const CHART_AUTH = path.join(root, "deploy/helm/repody-auth");
const VALUES_BASE = path.join(CHART_DIR, "values.yaml");
const VALUES_LOCAL = path.join(CHART_DIR, "values-local.yaml");
const VALUES_DATA_LOCAL = path.join(CHART_DATA, "values-local.yaml");
const VALUES_QUEUE_LOCAL = path.join(CHART_QUEUE, "values-local.yaml");
const VALUES_AUTH_LOCAL = path.join(CHART_AUTH, "values-local.yaml");
const VALUES_LOCAL_IMAGES = path.join(CHART_DIR, "values-local-images.yaml");
const LOCAL_ADDONS_OBS = path.join(root, "deploy/k8s/local-addons-obs.yaml");
const {
  applyJson,
  capture,
  captureNoShell,
  captureOptional,
  captureOptionalNoShell,
  captureWithInput,
  run,
  runNoShell,
} = createProcessAdapter(root);
const { cmdHosts, ensureHostsHint } = createHostsCommands({ root, run });
const {
  connectRegistryToKind,
  ensureLocalRegistry,
  localRegistryRef,
  pushManyToLocalRegistry,
  repodyImagesInRegistry,
  thirdPartyImagesWarm,
} = createLocalRegistryCommands({
  captureNoShell,
  connectHarborToKind: () =>
    connectHarborToKind({ registryHost: REGISTRY_CONFIG.registryHost }),
  heading,
  harborAdminPassword: REGISTRY_CONFIG.harborAdminPassword,
  harborHost: REGISTRY_CONFIG.registryHost,
  harborHttpPort: REGISTRY_CONFIG.harborHttpPort,
  harborProject: REGISTRY_CONFIG.harborProject,
  kindPlatform: KIND_PLATFORM,
  localRegistry: LOCAL_REGISTRY,
  run,
});
const {
  buildAppHelmSets,
  buildAuthHelmSets,
  buildDataHelmSets,
  buildQueueHelmSets,
  buildRegistryHelmSets,
  collectHelmImages,
  ensureHelmDependencies,
  externalInferenceHelmSets,
} = createLocalHelmCommands({
  capture,
  chartDirs: {
    app: CHART_DIR,
    data: CHART_DATA,
    queue: CHART_QUEUE,
    auth: CHART_AUTH,
  },
  hasFlag,
  keycloakImage: KEYCLOAK_IMAGE,
  localRegistry: LOCAL_REGISTRY,
  localRegistryRef,
  pinnedImages: PINNED_IMAGES,
  run,
  truthyEnv,
  valuesBase: VALUES_BASE,
  valuesLocal: VALUES_LOCAL,
});
const {
  authHostAliasHelmSets,
  ensureEnvoyNodePort,
  gatewayProgrammed,
  gatewayProgress,
  installEnvoyGatewayController,
} = createGatewayCommands({
  authHost: LOCAL_HOSTS.auth,
  authNamespace: NS_AUTH,
  capture,
  captureOptional,
  chartDir: CHART_DIR,
  envoyChart: ENVOY_CHART,
  envoyNamespace: ENVOY_NS,
  envoyVersion: ENVOY_VERSION,
  heading,
  namespace: NS,
  run,
  waitFor,
});
const { configureArgoRepositoryCredentials, installArgoCd, registerLocalGitOpsRootApp } =
  createArgoCommands({
  applyJson,
  argoInstallUrl: ARGO_INSTALL_URL,
  argoLocalRootApp: LOCAL_ARGO_ROOT,
  argoNamespace: ARGO_NS,
  argoRepoUrl: ARGO_REPO_URL,
  capture,
  captureOptional,
  captureWithInput,
  ensureNamespace,
  heading,
  run,
  runNoShell,
  waitFor,
  waitForWithProgress,
});

const { followPlatformLogs, prepareHelmUpgrade } = createLogCommands({ capture, root, run });
const {
  handoffHelmReleasesToArgo,
  refreshArgoApplications,
  waitForArgoApplicationsSynced,
} = createGitOpsHandoffCommands({ captureOptional, run, argoNamespace: ARGO_NS });

function resolveImageTags(minimal) {
  if (process.env.REPODY_IMAGE_TAG) {
    const tag = process.env.REPODY_IMAGE_TAG;
    return { backend: tag, web: tag, label: tag };
  }
  if (!minimal) {
    const sha = gitShortSha(root);
    return { backend: sha, web: sha, label: `git=${sha}` };
  }
  return resolveLocalImageTags(root);
}

function kindClusterExists() {
  try {
    return capture("kind", ["get", "clusters"]).split("\n").includes(CLUSTER);
  } catch {
    return false;
  }
}

function kindClusterReachable() {
  const useContext = spawnSync(
    "kubectl",
    ["config", "use-context", `kind-${CLUSTER}`],
    {
      stdio: "ignore",
      cwd: root,
      shell: process.platform === "win32",
    },
  );
  if (useContext.status !== 0) {
    return false;
  }
  const clusterInfo = spawnSync("kubectl", ["cluster-info"], {
    stdio: "ignore",
    cwd: root,
    shell: process.platform === "win32",
  });
  return clusterInfo.status === 0;
}

function startStoppedKindNodes() {
  let names = "";
  try {
    names = capture("docker", [
      "ps",
      "-a",
      "--filter",
      `label=io.x-k8s.kind.cluster=${CLUSTER}`,
      "--filter",
      "status=exited",
      "--format",
      "{{.Names}}",
    ]);
  } catch {
    return false;
  }
  const containers = names
    .split("\n")
    .map((name) => name.trim())
    .filter(Boolean);
  if (containers.length === 0) {
    return false;
  }

  heading(`Starting stopped kind nodes for ${CLUSTER}`);
  for (const name of containers) {
    console.error(`… starting ${name}`);
    run("docker", ["start", name]);
  }
  return true;
}

function ensureKindCluster({ reset, kindConfig }) {
  if (reset && kindClusterExists()) {
    run("kind", ["delete", "cluster", "--name", CLUSTER]);
  }

  if (kindClusterExists()) {
    if (!kindClusterReachable()) {
      const restarted = startStoppedKindNodes();
      if (restarted) {
        waitFor(
          () => kindClusterReachable(),
          `kind cluster ${CLUSTER} API`,
          120_000,
          3_000,
        );
        console.error(`✓ kind cluster ${CLUSTER} was stopped; nodes restarted`);
      } else {
        console.error(
          `✗ kind cluster ${CLUSTER} is registered but unreachable; recreating`,
        );
        run("kind", ["delete", "cluster", "--name", CLUSTER]);
      }
    } else {
      console.error(`✓ kind cluster ${CLUSTER} already exists; reusing it`);
    }
  }

  if (!kindClusterExists()) {
    run("kind", ["create", "cluster", "--config", kindConfig]);
    run("kubectl", ["cluster-info"]);
  }

  run("kubectl", ["config", "use-context", `kind-${CLUSTER}`]);
}

function ensureNamespace(name) {
  const exists = spawnSync("kubectl", ["get", "namespace", name], {
    stdio: "ignore",
    cwd: root,
    shell: process.platform === "win32",
  });
  if (exists.status === 0) {
    console.error(`✓ namespace/${name}`);
    return;
  }
  run("kubectl", ["create", "namespace", name]);
}

const REPODY_CRITICAL_POD_PREFIXES = [
  "repody-api-",
  "repody-web-",
  "repody-worker-",
];

function wantsObservability(minimal) {
  if (minimal) return false;
  return hasFlag("--with=obs") || truthyEnv("REPODY_K8S_LOCAL_OBS");
}

function cleanupStaleLocalResources() {
  captureOptional("kubectl", [
    "-n",
    "default",
    "delete",
    "deploy/repody-api",
    "--ignore-not-found",
  ]);
  captureOptional("kubectl", [
    "-n",
    NS_APP,
    "delete",
    "jobs",
    "--field-selector",
    "status.successful=1",
    "--ignore-not-found",
  ]);
}

function removeLocalObservability() {
  captureOptional("kubectl", [
    "delete",
    "-f",
    LOCAL_ADDONS_OBS,
    "--ignore-not-found",
    "--wait=false",
  ]);
}

/** @param {string} name @param {string} phase */
function repodyPodGroup(name, phase) {
  if (phase === "Succeeded" || phase === "Failed") return "Completed jobs";
  if (name.startsWith("local-")) return "Observability";
  if (/^repody-(api|web|worker)-/.test(name)) return "Platform";
  if (/^(repody-auth-)?keycloak-/.test(name)) return "Auth";
  if (/^repody-(data-)?postgresql|^repody-(data-)?redis|^repody-(data-)?minio/.test(name)) {
    return "Data";
  }
  if (/^repody-(queue-)?(hatchet|rabbitmq)/.test(name)) return "Queue";
  if (/^repody-[a-z0-9]+-/.test(name)) return "Completed jobs";
  return "Other";
}

function printGroupedPodStatus(namespace) {
  const raw = captureOptional("kubectl", [
    "-n",
    namespace,
    "get",
    "pods",
    "--no-headers",
    "-o",
    "custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[*].ready,STATUS:.status.phase",
  ]);
  if (!raw || raw.startsWith("error")) {
    console.error(`(${namespace}: no pods)`);
    return;
  }
  const groups = new Map();
  for (const line of raw.split(/\r?\n/).map((row) => row.trim()).filter(Boolean)) {
    const parts = line.split(/\s+/);
    const name = parts[0] ?? "";
    const phase = parts.at(-1) ?? "";
    const ready = parts.slice(1, -1).join(" ");
    const group = repodyPodGroup(name, phase);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push({ name, ready, phase });
  }
  const order = ["Platform", "Data", "Queue", "Auth", "Observability", "Completed jobs", "Other"];
  for (const title of order) {
    const pods = groups.get(title);
    if (!pods?.length) continue;
    console.error(`\n${title} (${pods.length})`);
    for (const pod of pods) {
      const status =
        pod.phase === "Running" ? pod.ready || pod.phase : pod.phase;
      console.error(`  ${pod.name.padEnd(42)} ${status}`);
    }
  }
}

function printAllGroupedPodStatus() {
  for (const namespace of LOCAL_NAMESPACES) {
    heading(`Pods in ${namespace}`);
    printGroupedPodStatus(namespace);
  }
}

function namespacePodsReady(namespace) {
  try {
    const states = capture("kubectl", [
      "-n",
      namespace,
      "get",
      "pods",
      "--no-headers",
      "-o",
      "custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[*].ready,PHASE:.status.phase",
    ]);
    const lines = states.split("\n").map((line) => line.trim()).filter(Boolean);
    if (lines.length === 0) return namespace !== NS_APP;
    return lines.every((line) => {
      const parts = line.split(/\s+/);
      const name = parts[0] ?? "";
      const phase = parts.at(-1);
      const ready = parts.slice(1, -1).join(" ");
      if (phase === "Succeeded" || phase === "Failed") return true;
      if (name.includes("worker-token") || name.includes("-migration")) return true;
      if (/^repody-[a-z0-9]+-[a-z0-9]+$/.test(name)) return true;
      return phase === "Running" && ready && !ready.includes("false");
    });
  } catch {
    return false;
  }
}

function repodyPodsReady() {
  return LOCAL_NAMESPACES.every((namespace) => namespacePodsReady(namespace));
}

function hatchetControlPlaneReady() {
  try {
    const ready = captureOptionalNoShell("kubectl", [
      "-n",
      NS_QUEUE,
      "get",
      "deploy",
      "repody-hatchet-engine",
      "-o",
      "jsonpath={.status.readyReplicas}",
    ]);
    return ready === "1";
  } catch {
    return false;
  }
}

function repodyPodFailureReason() {
  try {
    const hatchetReady = hatchetControlPlaneReady();
    const raw = captureOptionalNoShell("kubectl", [
      "-n",
      NS_APP,
      "get",
      "pods",
      "-o",
      "json",
    ]);
    if (!raw) return null;
    const items = JSON.parse(raw).items ?? [];
    for (const pod of items) {
      const name = pod.metadata?.name ?? "";
      if (!REPODY_CRITICAL_POD_PREFIXES.some((prefix) => name.startsWith(prefix))) {
        continue;
      }
      if (name.startsWith("repody-worker-") && !hatchetReady) {
        continue;
      }
      const startedAt = pod.status?.startTime
        ? Date.parse(pod.status.startTime)
        : Date.now();
      const ageMs = Date.now() - startedAt;
      const statuses = [
        ...(pod.status?.initContainerStatuses ?? []),
        ...(pod.status?.containerStatuses ?? []),
      ];
      for (const status of statuses) {
        const waiting = status.state?.waiting;
        const restarts = status.restartCount ?? 0;
        if (
          waiting?.reason === "CrashLoopBackOff" &&
          ageMs < 120_000 &&
          restarts < 3
        ) {
          continue;
        }
        if (
          waiting?.reason === "CrashLoopBackOff" ||
          waiting?.reason === "ImagePullBackOff" ||
          waiting?.reason === "ErrImagePull"
        ) {
          return `${name} (${status.name}): ${waiting.reason}${waiting.message ? ` — ${waiting.message}` : ""}`;
        }
        const terminated = status.state?.terminated;
        if (
          terminated?.reason === "Error" &&
          restarts >= 3
        ) {
          return `${name} (${status.name}): ${terminated.reason} (exit ${terminated.exitCode})`;
        }
      }
    }
    return null;
  } catch {
    return null;
  }
}

function repodyPodsProgress() {
  console.error("\n--- Repody pod status ---");
  for (const namespace of LOCAL_NAMESPACES) {
    console.error(`\n[${namespace}]`);
    console.error(
      captureOptional("kubectl", [
        "-n",
        namespace,
        "get",
        "pods",
        "-o",
        "wide",
      ]),
    );
  }

  console.error("\n--- Waiting / terminated container reasons (app) ---");
  const reasons = captureOptionalNoShell("kubectl", [
    "-n",
    NS_APP,
    "get",
    "pods",
    "-o",
    "jsonpath={range .items[*]}{.metadata.name}{': init='}{range .status.initContainerStatuses[*]}{.name}{' ready='}{.ready}{' waiting='}{.state.waiting.reason}{' terminated='}{.state.terminated.reason}{'; '}{end}{' containers='}{range .status.containerStatuses[*]}{.name}{' ready='}{.ready}{' waiting='}{.state.waiting.reason}{' terminated='}{.state.terminated.reason}{' restarts='}{.restartCount}{'; '}{end}{'\\n'}{end}",
  ]);
  console.error(reasons || "(no container status yet)");

  console.error("\n--- Recent Repody events (app) ---");
  console.error(
    captureOptional("kubectl", [
      "-n",
      NS_APP,
      "get",
      "events",
      "--sort-by=.lastTimestamp",
    ])
      .split("\n")
      .slice(-30)
      .join("\n"),
  );

  const pods = LOCAL_NAMESPACES.flatMap((namespace) =>
    captureOptional("kubectl", [
      "-n",
      namespace,
      "get",
      "pods",
      "-o",
      "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}",
    ])
      .split("\n")
      .map((pod) => pod.trim())
      .filter(Boolean)
      .filter(
        (pod) =>
          pod.startsWith("repody-api") ||
          pod.startsWith("repody-web") ||
          pod.startsWith("repody-worker") ||
          pod.startsWith("repody-hatchet") ||
          pod.startsWith("repody-auth-keycloak") ||
          pod.startsWith("keycloak-"),
      )
      .map((pod) => ({ namespace, pod })),
  );

  for (const { namespace, pod } of pods.slice(0, 8)) {
    console.error(`\n--- Recent logs: ${namespace}/${pod} ---`);
    console.error(
      captureOptional("kubectl", [
        "-n",
        namespace,
        "logs",
        pod,
        "--all-containers=true",
        "--tail=40",
        "--prefix=true",
      ]),
    );
  }
  console.error("");
}

function syncPlatformSecrets() {
  run("node", ["deploy/scripts/sync-platform-secrets.mjs"]);
}

function hatchetClientTokenReady() {
  const token = captureOptionalNoShell("kubectl", [
    "-n",
    NS_QUEUE,
    "get",
    "secret/hatchet-client-config",
    "-o",
    "jsonpath={.data.HATCHET_CLIENT_TOKEN}",
  ]);
  return Boolean(token);
}

function installLocalHelmStack({
  minimal,
  argoOwnsApp = false,
  backendTag,
  webTag,
  helmValueFiles,
  authHelmSets,
}) {
  const appHelmSets = [
    ...buildAppHelmSets({
      backendTag,
      webTag,
      omitImageTags: !minimal,
    }),
    ...externalInferenceHelmSets(),
  ];

  heading("Installing platform data plane (PostgreSQL, Redis, MinIO)");
  ensureNamespace(NS_DATA);
  prepareHelmUpgrade(NS_DATA, "repody-data");
  run("helm", [
    "upgrade",
    "--install",
    "repody-data",
    CHART_DATA,
    "-n",
    NS_DATA,
    "-f",
    path.join(CHART_DATA, "values.yaml"),
    "-f",
    VALUES_DATA_LOCAL,
    ...buildDataHelmSets(),
    "--timeout",
    "15m",
  ]);

  heading("Installing platform queue (Hatchet)");
  ensureNamespace(NS_QUEUE);
  prepareHelmUpgrade(NS_QUEUE, "repody-queue");
  run("helm", [
    "upgrade",
    "--install",
    "repody-queue",
    CHART_QUEUE,
    "-n",
    NS_QUEUE,
    "-f",
    path.join(CHART_QUEUE, "values.yaml"),
    "-f",
    VALUES_QUEUE_LOCAL,
    ...buildQueueHelmSets(),
    "--timeout",
    "15m",
  ]);

  waitForWithProgress(
    () => hatchetClientTokenReady(),
    "Hatchet worker token in repody-queue",
    300_000,
    5_000,
  );
  syncPlatformSecrets();

  heading("Installing platform auth (Keycloak)");
  ensureNamespace(NS_AUTH);
  run("helm", [
    "upgrade",
    "--install",
    "repody-auth",
    CHART_AUTH,
    "-n",
    NS_AUTH,
    "-f",
    path.join(CHART_AUTH, "values.yaml"),
    "-f",
    VALUES_AUTH_LOCAL,
    ...buildAuthHelmSets(),
    "--timeout",
    "10m",
  ]);

  if (argoOwnsApp) {
    ensureNamespace(NS_APP);
    console.error(
      "ok: app plane owned by Argo CD (repody-local-app) — skipping Helm repody release",
    );
    return;
  }

  heading("Installing Repody app (API, web, workers, Gateway)");
  ensureNamespace(NS_APP);
  prepareHelmUpgrade(NS_APP, "repody");
  run("helm", [
    "upgrade",
    "--install",
    "repody",
    CHART_DIR,
    "-n",
    NS_APP,
    ...helmValueFiles.flatMap((file) => ["-f", file]),
    ...appHelmSets,
    ...authHelmSets,
    "--timeout",
    minimal ? "10m" : "15m",
  ]);
}

function cmdDown() {
  if (hasFlag("--cluster") || truthyEnv("REPODY_K8S_LOCAL_CLUSTER_DOWN")) {
    cmdDownCluster();
    return;
  }
  cmdDownSoft();
}

function cmdDownSoft() {
  heading("Stopping Repody app (keeping kind cluster + Harbor)");
  if (!kindClusterExists()) {
    console.error("ok: no kind cluster — nothing to stop");
    console.error("\n✓ Soft stop complete.\n");
    return;
  }
  const useContext = spawnSync(
    "kubectl",
    ["config", "use-context", `kind-${CLUSTER}`],
    { stdio: "ignore", shell: process.platform === "win32" },
  );
  if (useContext.status !== 0) {
    console.error(`ok: kind cluster ${CLUSTER} unreachable`);
    console.error("\n✓ Soft stop complete.\n");
    return;
  }
  for (const { release, namespace } of [
    { release: "repody", namespace: NS_APP },
    { release: "repody-auth", namespace: NS_AUTH },
    { release: "repody-queue", namespace: NS_QUEUE },
    { release: "repody-data", namespace: NS_DATA },
  ]) {
    const uninstall = spawnSync(
      "helm",
      ["uninstall", release, "-n", namespace, "--ignore-not-found", "--wait=false"],
      { stdio: "inherit", shell: process.platform === "win32" },
    );
    if (uninstall.status === 0) {
      console.error(`✓ Helm release ${release} removed`);
    }
  }
  captureOptional("kubectl", [
    "delete",
    "application",
    "repody-local-root",
    "-n",
    ARGO_NS,
    "--ignore-not-found",
    "--wait=false",
  ]);
  captureOptional("kubectl", [
    "delete",
    "-f",
    LOCAL_ADDONS_OBS,
    "--ignore-not-found",
    "--wait=false",
  ]);
  for (const namespace of [NS_QUEUE, NS_APP]) {
    for (const secret of ["hatchet-config", "hatchet-client-config", "hatchet-shared-config"]) {
      const del = spawnSync(
        "kubectl",
        ["delete", "secret", secret, "-n", namespace, "--ignore-not-found"],
        { stdio: "ignore", shell: process.platform === "win32" },
      );
      if (del.status === 0) {
        console.error(`✓ removed stale secret ${namespace}/${secret}`);
      }
    }
  }
  console.error(`
Redeploy:     pnpm dev
Code loop:    pnpm dev:sync   (Skaffold — after pnpm dev)
Full wipe:    pnpm stop --cluster  |  pnpm platform:reset
`);
}

function cmdDownCluster() {
  const del = spawnSync("kind", ["delete", "cluster", "--name", CLUSTER], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (del.status === 0) {
    console.error(`✓ kind cluster ${CLUSTER} removed`);
  } else {
    console.error(`ok: kind cluster ${CLUSTER} was not running`);
  }
  console.error("\n✓ Cluster stopped (Harbor still running — pnpm harbor:down to stop).\n");
}

function helmReleaseInstalled() {
  const result = spawnSync("helm", ["status", "repody", "-n", NS_APP], {
    stdio: "ignore",
    cwd: root,
    shell: process.platform === "win32",
  });
  return result.status === 0;
}

function deployedImageTagsMatch({ backend, web, minimal }) {
  if (!minimal) {
    try {
      const tag = readHelmImageTag(VALUES_LOCAL_IMAGES);
      return tag === backend && tag === web;
    } catch {
      return false;
    }
  }
  try {
    const raw = captureOptionalNoShell("helm", [
      "get",
      "values",
      "repody",
      "-n",
      NS_APP,
      "-o",
      "json",
    ]);
    if (!raw) return false;
    const values = JSON.parse(raw);
    const deployedBackend =
      values.images?.api?.tag ??
      values.images?.backend?.tag ??
      values.images?.worker?.tag;
    const deployedWeb = values.images?.web?.tag;
    return deployedBackend === backend && deployedWeb === web;
  } catch {
    return false;
  }
}

function printStackReadySummary({ minimal, withObs, tagLabel, argoPassword = "" }) {
  const obsBlock =
    minimal || !withObs
      ? ""
      : `
 Grafana (GW)      ${localUrl(LOCAL_HOSTS.grafana)}  (${LOCAL_CREDENTIALS.grafanaUser} / ${LOCAL_CREDENTIALS.grafanaPassword})
 Bugsink (GW)      ${localUrl(LOCAL_HOSTS.bugsink)}  (${LOCAL_CREDENTIALS.bugsinkUser} / ${LOCAL_CREDENTIALS.bugsinkPassword})`;
  const argoBlock = minimal
    ? ""
    : `
 Argo CD            https://127.0.0.1:8080  (pnpm argocd:port-forward — admin / ${argoPassword || "see kubectl secret"})`;

  console.error(`
══════════════════════════════════════════════════════════════════════
 Local Kubernetes stack is up (kind + Envoy Gateway${minimal ? "" : " + Argo CD"})
──────────────────────────────────────────────────────────────────────
 Web (Gateway)     ${localUrl(LOCAL_HOSTS.web)}
 API (Gateway)     ${localUrl(LOCAL_HOSTS.api, "/v1/healthz/live")}
 Files (Gateway)   ${localUrl(LOCAL_HOSTS.files)}
 Keycloak (GW)     ${localUrl(LOCAL_HOSTS.auth)}${obsBlock}${argoBlock}
──────────────────────────────────────────────────────────────────────
 Registry:      ${LOCAL_REGISTRY} (Harbor)
 Image tags:    ${tagLabel}
 Sign in: ${LOCAL_CREDENTIALS.keycloakUser} / ${LOCAL_CREDENTIALS.keycloakPassword}
 Open the app at ${localUrl(LOCAL_HOSTS.web)} — do not use localhost or 127.0.0.1 for sign-in.
${minimal ? " Fast path: --minimal (Helm deploy, content-hash tags)\n" : " GitOps: tags in values-local-images.yaml → pnpm gitops:publish -- --all → Argo Synced\n"}${!minimal && !withObs ? " Observability: off (add --with=obs for Grafana/Loki/Bugsink)\n" : ""} Daily loop:  pnpm dev:sync  (Skaffold — Python/TS hot sync, no rebuild)
 Stop app:    pnpm stop  (keeps kind + Harbor)
 Tear down:   pnpm stop --cluster  |  pnpm platform:reset
 Rebuild:     pnpm dev:build forces images; pnpm dev skips when content-hash unchanged
 Warm cache:  pnpm registry:warm  (third-party images once after clone)
${hasFlag("--logs") || truthyEnv("REPODY_K8S_LOCAL_LOGS") ? " Logs:        api/web/workers (add --logs-all for gateway+infra)\n" : ""}══════════════════════════════════════════════════════════════════════
`);
}

async function publishThirdPartyImages(tagHelmSets = []) {
  const helmImages = collectHelmImages(tagHelmSets);
  const publishImages = [
    ...helmImages.filter((img) => !img.startsWith("repody-")),
    KEYCLOAK_IMAGE,
  ];
  const unique = [...new Set(publishImages)];
  if (thirdPartyImagesWarm(unique)) {
    console.error(
      `ok: ${unique.length} third-party images already in ${LOCAL_REGISTRY}`,
    );
    return;
  }
  console.error(`Images to publish: ${unique.length}`);
  await pushManyToLocalRegistry(unique, {
    localBuild: false,
  });
}

async function cmdWarmRegistry() {
  requireDockerEngine();
  ensureLocalRegistry();
  heading("Preparing Helm chart dependencies");
  ensureHelmDependencies();
  heading("Warming Harbor (third-party images only)");
  await publishThirdPartyImages([
    "--set",
    "global.imageRegistry=",
    ...externalInferenceHelmSets(),
    "--set",
    "observability.otelEnabled=false",
  ]);
  console.error(
    `\n✓ Registry warm complete (${LOCAL_REGISTRY}). Repody images are built on pnpm dev when needed.\n`,
  );
}

function cmdStatus() {
  run("kubectl", ["config", "use-context", `kind-${CLUSTER}`]);
  run("kubectl", ["get", "nodes"]);
  printAllGroupedPodStatus();
  run("kubectl", ["-n", NS_APP, "get", "gateway,httproute"]);
  const argoPods = captureOptional("kubectl", [
    "-n",
    ARGO_NS,
    "get",
    "pods",
    "--no-headers",
  ]);
  if (argoPods && !argoPods.startsWith("error")) {
    const running = argoPods
      .split(/\r?\n/)
      .filter((line) => line && /\sRunning\s/.test(line)).length;
    const total = argoPods.split(/\r?\n/).filter(Boolean).length;
    console.error(`\nArgo CD (${ARGO_NS}): ${running}/${total} pods running`);
  }
  const argoApps = captureOptional("kubectl", [
    "-n",
    ARGO_NS,
    "get",
    "applications.argoproj.io",
  ]);
  if (argoApps) {
    console.error(argoApps);
  } else {
    console.error("(Argo CD not installed)");
  }
}

/**
 * @param {{ buildOnly: string, backendTag: string, webTag: string }} opts
 */
function startRepodyImageBuild({ buildOnly, backendTag, webTag }) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      "node",
      ["deploy/scripts/build-images.mjs", `--only=${buildOnly}`],
      {
        cwd: root,
        stdio: "inherit",
        shell: process.platform === "win32",
        env: {
          ...process.env,
          AUDIT_MINIO_PUBLIC_ENDPOINT: LOCAL_HOSTS.files,
          REPODY_BACKEND_IMAGE_TAG: backendTag,
          REPODY_WEB_IMAGE_TAG: webTag,
          REPODY_IMAGE_REGISTRY: "",
          REGISTRY: "",
        },
      },
    );
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`build-images.mjs exited ${code ?? 1}`));
    });
  });
}

function cmdUp() {
  cmdUpAsync().catch((error) => {
    console.error(error?.message || error);
    traceSummary();
    process.exit(1);
  });
}

async function cmdUpAsync() {
  requireDockerEngine();

  const minimal =
    hasFlag("--minimal") || truthyEnv("REPODY_K8S_LOCAL_MINIMAL");
  const withObs = wantsObservability(minimal);

  ensureLocalRegistry();
  heading("Preparing Helm chart dependencies");
  ensureHelmDependencies();

  const imageTags = resolveImageTags(minimal);
  const { backend: backendTag, web: webTag, label: tagLabel } = imageTags;
  const reset = hasFlag("--reset") || truthyEnv("REPODY_K8S_LOCAL_RESET");
  const forceBuild =
    hasFlag("--build") || truthyEnv("REPODY_K8S_LOCAL_BUILD");
  const forceDeploy =
    hasFlag("--deploy") || truthyEnv("REPODY_K8S_LOCAL_FORCE_DEPLOY");
  const tagHelmSets = [
    ...(minimal
      ? [
          "--set",
          `images.api.tag=${backendTag}`,
          "--set",
          `images.worker.tag=${backendTag}`,
          "--set",
          `images.web.tag=${webTag}`,
        ]
      : []),
    ...externalInferenceHelmSets(),
    ...(minimal ? ["--set", "observability.otelEnabled=false"] : []),
  ];

  const registryState = repodyImagesInRegistry({ backendTag, webTag });
  const clusterReuse =
    !reset && kindClusterExists() && kindClusterReachable();

  if (
    !reset &&
    !forceBuild &&
    !forceDeploy &&
    clusterReuse &&
    helmReleaseInstalled() &&
    deployedImageTagsMatch({ backend: backendTag, web: webTag, minimal }) &&
    repodyPodsReady() &&
    gatewayProgrammed()
  ) {
    console.error(
      "ok: warm stack (tags match, workloads healthy) — nothing to deploy",
    );
    ensureHostsHint();
    traceSummary();
    printStackReadySummary({ minimal, withObs, tagLabel });
    if (hasFlag("--logs") || truthyEnv("REPODY_K8S_LOCAL_LOGS")) {
      heading("Following platform logs (Ctrl+C to stop)");
      followPlatformLogs({
        minimal,
        verbose: hasFlag("--logs-all"),
        repodyNamespace: NS_APP,
        repodyNamespaces: LOCAL_NAMESPACES,
        envoyNamespace: ENVOY_NS,
        argoNamespace: ARGO_NS,
      });
    }
    return;
  }

  const explicitFast =
    hasFlag("--fast") || truthyEnv("REPODY_K8S_LOCAL_FAST");
  const fast =
    explicitFast ||
    (clusterReuse && helmReleaseInstalled() && !reset && !forceBuild);

  if (fast) {
    console.error("ok: fast path");
  } else {
    heading("Freeing host ports for Gateway ingress (80/443)");
    ensureGatewayPortsFree();
  }

  const buildBackend = forceBuild || !registryState.backendOk;
  const buildWeb = forceBuild || !registryState.webOk;
  const buildOnly =
    buildBackend && !buildWeb
      ? "backend"
      : !buildBackend && buildWeb
        ? "web"
        : "all";

  let imageBuildPromise = null;
  if (buildBackend || buildWeb) {
    if (buildOnly !== "all") {
      console.error(`… selective build: --only=${buildOnly}`);
    }
    console.error(
      `… building Repody images in parallel with cluster bootstrap (${tagLabel})`,
    );
    imageBuildPromise = startRepodyImageBuild({
      buildOnly,
      backendTag,
      webTag,
    });
  }

  const thirdPartyPromise = publishThirdPartyImages(tagHelmSets);

  heading(`${reset ? "Recreating" : "Creating/reusing"} kind cluster ${CLUSTER}`);
  ensureKindCluster({ reset, kindConfig: KIND_CONFIG });
  connectRegistryToKind();

  const infraPromise = minimal
    ? Promise.resolve().then(() => installEnvoyGatewayController())
    : Promise.all([
        Promise.resolve().then(() => installEnvoyGatewayController()),
        Promise.resolve().then(() => installArgoCd()),
      ]).then(() => {
        console.error("ok: Envoy Gateway + Argo CD ready");
      });

  if (imageBuildPromise) {
    heading(`Building Repody images (${tagLabel})`);
  }

  await Promise.all(
    [imageBuildPromise, thirdPartyPromise, infraPromise].filter(Boolean),
  );

  if (!imageBuildPromise) {
    console.error(
      `ok: repody images already in ${LOCAL_REGISTRY} (${tagLabel}); use --build to force`,
    );
  }

  const repodyPublish = [];
  if (buildBackend || !registryState.backendOk) {
    repodyPublish.push(`repody-backend:${backendTag}`);
  }
  if (buildWeb || !registryState.webOk) {
    repodyPublish.push(`repody-web:${webTag}`);
  }
  if (repodyPublish.length > 0) {
    heading("Publishing images to Harbor");
    console.error(`Repody tags: ${tagLabel}`);
    await pushManyToLocalRegistry(repodyPublish, { localBuild: true });
  }

  if (!minimal) {
    bumpHelmImageTags(VALUES_LOCAL_IMAGES, backendTag);
    console.error(`ok: values-local-images.yaml → ${backendTag}`);
  }

  const authHelmSets = authHostAliasHelmSets();
  const skipHelmUpgrade =
    fast &&
    !forceDeploy &&
    helmReleaseInstalled() &&
    deployedImageTagsMatch({ backend: backendTag, web: webTag, minimal });

  heading("Preparing namespaces and Gateway edge");
  for (const namespace of LOCAL_NAMESPACES) {
    ensureNamespace(namespace);
  }
  run("kubectl", [
    "apply",
    "-f",
    path.join(root, "deploy/k8s/envoy-proxy-kind-nodeport.yaml"),
  ]);

  if (skipHelmUpgrade) {
    console.error("ok: deployed image tags match — skipping Helm upgrade");
  } else {
    heading(
      minimal
        ? "Installing Repody stack via Helm (4 namespaces)"
        : "Bootstrapping platform via Helm (data/queue/auth); Argo CD owns all planes after registration",
    );
    installLocalHelmStack({
      minimal,
      argoOwnsApp: !minimal,
      backendTag,
      webTag,
      helmValueFiles: [
        VALUES_BASE,
        VALUES_LOCAL,
        ...(minimal ? [] : [VALUES_LOCAL_IMAGES]),
      ],
      authHelmSets,
    });

    if (!authHelmSets.length) {
      console.error(
        "ok: web auth-host-alias init container maps Keycloak for server-side OIDC (no second Helm upgrade)",
      );
    } else {
      console.error(
        `ok: gatewayApi.authHostAliasIp set in initial Helm upgrade (${authHelmSets[1]})`,
      );
    }
  }

  if (!minimal) {
    if (withObs) {
      heading("Installing local observability addons (Grafana/Loki/Promtail/Tempo/Bugsink)");
      run("kubectl", ["apply", "-f", LOCAL_ADDONS_OBS]);
    } else {
      removeLocalObservability();
      console.error("ok: observability off — use --with=obs to install Grafana/Loki/Bugsink");
    }

    heading("Registering Argo CD app-of-apps (GitOps bootstrap from Git)");
    configureArgoRepositoryCredentials();
    registerLocalGitOpsRootApp();

    heading("Handing workload ownership to Argo CD");
    handoffHelmReleasesToArgo();
    refreshArgoApplications();
    try {
      await waitForArgoApplicationsSynced(fast ? 300_000 : 900_000);
      syncPlatformSecrets();
    } catch {
      console.error(
        "warn: Argo CD apps not fully Synced yet — run pnpm gitops:publish -- --all or wait for automated sync",
      );
    }
  } else {
    console.error("ok: --minimal — skipping Argo CD and local addons");
  }

  cleanupStaleLocalResources();

  if (
    !minimal &&
    (hasFlag("--push") || truthyEnv("REPODY_GITOPS_PUSH"))
  ) {
    heading("GitOps: commit, push, and Argo CD sync");
    run("node", [
      "deploy/scripts/gitops-publish-local.mjs",
      "--commit",
      "--push",
      "--sync",
    ]);
  } else if (!minimal) {
    console.error(
      "ok: bump values-local-images.yaml locally — run pnpm gitops:publish -- --all for Argo Synced",
    );
  }

  const alreadyHealthy =
    fast && repodyPodsReady() && gatewayProgrammed();

  if (alreadyHealthy) {
    console.error("ok: --fast workloads already ready; skipping long readiness wait");
  } else {
    heading("Waiting for Repody workloads");
    waitForWithProgress(
      () => {
        const failure = repodyPodFailureReason();
        if (failure) {
          repodyPodsProgress();
          throw new Error(
            `Repody workload failed (${failure}). Fix the pod, then re-run pnpm dev.`,
          );
        }
        return repodyPodsReady();
      },
      "all Repody namespace pods ready",
      fast ? 300_000 : 600_000,
      5_000,
      repodyPodsProgress,
      30_000,
    );
    waitForWithProgress(
      () => gatewayProgrammed(),
      "Gateway API programmed",
      fast ? 120_000 : 300_000,
      5_000,
      gatewayProgress,
      30_000,
    );
  }

  if (fast && alreadyHealthy) {
    console.error("ok: --fast skipping Gateway HTTP smoke checks");
  } else if (!fast) {
    heading("Verifying API + Auth.js via Gateway");
    ensureEnvoyNodePort();
    const apiTimeout = 120_000;
    await Promise.all([
      Promise.resolve().then(() =>
        waitFor(
          () => {
            try {
              const curl = process.platform === "win32" ? "curl.exe" : "curl";
              const body = captureNoShell(curl, [
                "-sf",
                "--max-time",
                "5",
                "-H",
                `Host: ${LOCAL_HOSTS.api}`,
                "http://127.0.0.1/v1/healthz/live",
              ]);
              return (
                body.includes('"status":"ok"') || body.includes('"status": "ok"')
              );
            } catch {
              return false;
            }
          },
          `API health via Gateway (${localUrl(LOCAL_HOSTS.api)})`,
          apiTimeout,
        ),
      ),
      Promise.resolve().then(() =>
        waitFor(
          () => {
            try {
              const curl = process.platform === "win32" ? "curl.exe" : "curl";
              const body = captureNoShell(curl, [
                "-sf",
                "--max-time",
                "10",
                "-H",
                `Host: ${LOCAL_HOSTS.web}`,
                "http://127.0.0.1/api/auth/providers",
              ]);
              return body.includes('"keycloak"');
            } catch {
              return false;
            }
          },
          `Auth.js Keycloak provider (${localUrl(LOCAL_HOSTS.web)})`,
          apiTimeout,
        ),
      ),
    ]);
  }

  let argoPassword = "";
  if (!minimal) {
    argoPassword =
      "(run: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d)";
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
  }

  ensureHostsHint();
  traceSummary();
  printStackReadySummary({ minimal, withObs, tagLabel, argoPassword });

  if (hasFlag("--logs") || truthyEnv("REPODY_K8S_LOCAL_LOGS")) {
    heading("Following platform logs (Ctrl+C to stop)");
    followPlatformLogs({
      minimal,
      verbose: hasFlag("--logs-all"),
      repodyNamespace: NS_APP,
      repodyNamespaces: LOCAL_NAMESPACES,
      envoyNamespace: ENVOY_NS,
      argoNamespace: ARGO_NS,
    });
  }
}

function cmdLogs() {
  const minimal =
    hasFlag("--minimal") || truthyEnv("REPODY_K8S_LOCAL_MINIMAL");
  const withObs = wantsObservability(minimal);
  heading("Following platform logs (Ctrl+C to stop)");
  followPlatformLogs({
    minimal,
    verbose: hasFlag("--logs-all"),
    repodyNamespace: NS_APP,
    repodyNamespaces: LOCAL_NAMESPACES,
    envoyNamespace: ENVOY_NS,
    argoNamespace: ARGO_NS,
  });
}

const sub = process.argv[2] ?? "up";
if (sub === "up") cmdUp();
else if (sub === "down") cmdDown();
else if (sub === "warm-registry") {
  cmdWarmRegistry().catch((error) => {
    console.error(error?.message || error);
    process.exit(1);
  });
}
else if (sub === "status") cmdStatus();
else if (sub === "hosts") cmdHosts();
else if (sub === "logs") cmdLogs();
else {
  console.error(
    "Usage: pnpm k8s:local [up|down|warm-registry|status|hosts|logs] [--reset] [--build] [--deploy] [--fast] [--minimal] [--with=obs] [--push] [--cluster] [--trace] [--logs] [--logs-all]",
  );
  process.exit(1);
}
