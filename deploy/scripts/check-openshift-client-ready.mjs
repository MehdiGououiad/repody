#!/usr/bin/env node
/**
 * Client-readiness checks for OpenShift client test lab.
 *
 *   node deploy/scripts/check-openshift-client-ready.mjs [--namespace repody]
 *     [--profile=bundled|external] [--registry=harbor|openshift]
 */
import { spawnSync } from "node:child_process";
import { resolveExecutable } from "./runtime-env.mjs";

const argv = process.argv.slice(2);
const nsIdx = argv.indexOf("--namespace");
const ns = nsIdx >= 0 ? argv[nsIdx + 1] : "repody";
const profileArg = argv.find((a) => a.startsWith("--profile="));
const registryArg = argv.find((a) => a.startsWith("--registry="));
const profile = profileArg?.slice("--profile=".length) === "external" ? "external" : "bundled";
const registryMode = registryArg?.slice("--registry=".length) === "openshift" ? "openshift" : "harbor";

const failures = [];
const warnings = [];

function kubectl(args) {
  return spawnSync(resolveExecutable("kubectl"), args, { encoding: "utf8" });
}

function kubectlOut(args) {
  const result = kubectl(args);
  return result.status === 0 ? (result.stdout ?? "").trim() : "";
}

function requireOk(condition, message) {
  if (!condition) failures.push(message);
}

function warnIf(condition, message) {
  if (condition) warnings.push(message);
}

function main() {
  if (!kubectlOut(["config", "current-context"])) {
    console.error("error: kubectl has no current context");
    process.exit(1);
  }

  const enforce = kubectlOut([
    "get",
    "namespace",
    ns,
    "-o",
    "jsonpath={.metadata.labels.pod-security\\.kubernetes\\.io/enforce}",
  ]);
  requireOk(
    enforce === "restricted" || enforce === "baseline",
    `namespace ${ns} must use pod-security.kubernetes.io/enforce=restricted or baseline (got: ${enforce || "unset"})`,
  );
  warnIf(enforce === "baseline", `namespace ${ns} uses enforce=baseline; prefer restricted for production-shaped labs`);

  const esNames =
    profile === "external"
      ? ["registry-pull-secret", "repody-runtime-secrets"]
      : [
          "registry-pull-secret",
          "repody-data-postgresql",
          "repody-data-redis",
          "repody-data-minio",
          "repody-runtime-secrets",
        ];
  for (const name of esNames) {
    const ready = kubectlOut([
      "get",
      "externalsecret",
      name,
      "-n",
      ns,
      "-o",
      'jsonpath={.status.conditions[?(@.type=="Ready")].status}',
    ]);
    requireOk(ready === "True", `ExternalSecret ${name} not Ready (status: ${ready || "missing"})`);
  }

  const storeYaml = kubectlOut(["get", "clustersecretstore", "vault-repody", "-o", "yaml"]);
  requireOk(storeYaml.includes("conditions:"), "ClusterSecretStore vault-repody should define spec.conditions");

  const netpolCount = kubectlOut(["get", "networkpolicy", "-n", ns, "--no-headers"]);
  const netpolLines = netpolCount ? netpolCount.split("\n").filter(Boolean).length : 0;
  requireOk(netpolLines > 0, `expected NetworkPolicies in ${ns} (enterprise hardening)`);

  const logJson = kubectlOut([
    "get",
    "configmap",
    "repody-config",
    "-n",
    ns,
    "-o",
    "jsonpath={.data.AUDIT_LOG_JSON}",
  ]);
  requireOk(logJson === "true", "repody-config must set AUDIT_LOG_JSON=true (structured JSON logs)");

  const otelEnabled = kubectlOut([
    "get",
    "configmap",
    "repody-config",
    "-n",
    ns,
    "-o",
    "jsonpath={.data.AUDIT_OTEL_ENABLED}",
  ]);
  if (otelEnabled === "true") {
    const otelReady = kubectlOut([
      "get",
      "deploy",
      "otel-collector-opentelemetry-collector",
      "-n",
      "observability",
      "-o",
      "jsonpath={.status.readyReplicas}",
    ]);
    requireOk(
      otelReady === "1",
      "otel-collector in observability namespace should have 1 ready replica",
    );
  } else {
    warnIf(otelEnabled !== "false", "AUDIT_OTEL_ENABLED not set; skipping otel-collector check");
  }

  const registryData = kubectlOut([
    "get",
    "secret",
    "registry-pull-secret",
    "-n",
    ns,
    "-o",
    "jsonpath={.data.\\.dockerconfigjson}",
  ]);
  if (registryData) {
    try {
      const decoded = JSON.parse(Buffer.from(registryData, "base64").toString("utf8"));
      const hosts = Object.keys(decoded.auths ?? {});
      if (registryMode === "openshift") {
        const hasInternal = hosts.some((h) => h.includes("image-registry.openshift-image-registry.svc"));
        requireOk(hasInternal, "registry-pull-secret missing internal OpenShift registry auth host");
      } else {
        const hasHarbor = hosts.some(
          (h) => h.includes("5080") || h.includes("harbor") || h.includes("crc.testing") || h.includes("crc.internal"),
        );
        requireOk(hasHarbor || hosts.length > 0, "registry-pull-secret should include Harbor registry auth");
      }
    } catch {
      failures.push("registry-pull-secret .dockerconfigjson is not valid JSON");
    }
  }

  const helmJson = spawnSync("helm", ["list", "-n", ns, "-o", "json"], { encoding: "utf8" });
  let releases = [];
  if (helmJson.status === 0) {
    try {
      releases = JSON.parse(helmJson.stdout || "[]");
    } catch {
      releases = [];
    }
  }
  const expectedReleases =
    profile === "external" ? ["repody-auth", "repody"] : ["repody-data", "repody-auth", "repody"];
  for (const release of expectedReleases) {
    const row = releases.find((r) => r.name === release);
    if (!row) {
      warnIf(true, `helm release ${release} not found in ${ns} (may be Argo CD managed)`);
    } else {
      requireOk(row.status === "deployed", `helm release ${release} status is ${row.status}, expected deployed`);
    }
  }

  const apiReady = kubectlOut([
    "get",
    "deploy",
    "repody-api",
    "-n",
    ns,
    "-o",
    "jsonpath={.status.readyReplicas}",
  ]);
  requireOk(apiReady === "1", `repody-api ready replicas: ${apiReady || "0"}`);

  const vaultDev = kubectlOut([
    "get",
    "statefulset",
    "vault",
    "-n",
    "vault",
    "-o",
    "jsonpath={.spec.template.spec.containers[0].env[?(@.name==\"VAULT_DEV_ROOT_TOKEN_ID\")].value}",
  ]);
  warnIf(Boolean(vaultDev), "Vault dev mode detected — acceptable for client test lab only");

  if (warnings.length) {
    console.warn("\nWarnings:");
    for (const w of warnings) console.warn(`  - ${w}`);
  }

  if (failures.length) {
    console.error("\nClient readiness FAILED:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }

  console.log(`\nClient readiness OK (${profile}, registry=${registryMode}, namespace ${ns}).\n`);
}

main();
