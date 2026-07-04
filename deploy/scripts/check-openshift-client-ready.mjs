#!/usr/bin/env node
/**
 * Client-readiness checks for OpenShift bundled lab / handoff validation.
 *
 *   node deploy/scripts/check-openshift-client-ready.mjs [--namespace repody]
 *
 * Exits 0 when the cluster matches production-shaped client expectations.
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const ns = process.argv.includes("--namespace")
  ? process.argv[process.argv.indexOf("--namespace") + 1]
  : "repody";

const failures = [];
const warnings = [];

function resolveOc() {
  const fromEnv = process.env.CRC_OC?.trim() || process.env.OC?.trim();
  if (fromEnv && existsSync(fromEnv)) return fromEnv;
  const candidates = [
    path.join(os.homedir(), ".crc", "bin", "oc", "oc.exe"),
    path.join(os.homedir(), ".crc", "bin", "oc.exe"),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return "oc";
}

function oc(args) {
  return spawnSync(resolveOc(), args, { encoding: "utf8" });
}

function ocOut(args) {
  const result = oc(args);
  return result.status === 0 ? (result.stdout ?? "").trim() : "";
}

function requireOk(condition, message) {
  if (!condition) failures.push(message);
}

function warnIf(condition, message) {
  if (condition) warnings.push(message);
}

function main() {
  if (!ocOut(["whoami"])) {
    console.error("error: oc not logged in");
    process.exit(1);
  }

  const enforce = ocOut(["get", "namespace", ns, "-o", "jsonpath={.metadata.labels.pod-security\\.kubernetes\\.io/enforce}"]);
  requireOk(
    enforce === "restricted" || enforce === "baseline",
    `namespace ${ns} must use pod-security.kubernetes.io/enforce=restricted or baseline (got: ${enforce || "unset"})`,
  );
  warnIf(enforce === "baseline", `namespace ${ns} uses enforce=baseline; prefer restricted for production-shaped labs`);

  const esNames = [
    "registry-pull-secret",
    "repody-data-postgresql",
    "repody-data-redis",
    "repody-data-minio",
    "repody-runtime-secrets",
  ];
  for (const name of esNames) {
    const ready = ocOut([
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

  const storeYaml = ocOut(["get", "clustersecretstore", "vault-repody", "-o", "yaml"]);
  requireOk(storeYaml.includes("conditions:"), "ClusterSecretStore vault-repody should define spec.conditions (namespace scope)");

  const netpolCount = ocOut(["get", "networkpolicy", "-n", ns, "--no-headers"]);
  const netpolLines = netpolCount ? netpolCount.split("\n").filter(Boolean).length : 0;
  requireOk(netpolLines > 0, `expected NetworkPolicies in ${ns} (enterprise hardening)`);

  const kcAdmin = ocOut([
    "get",
    "secret",
    "repody-runtime-secrets",
    "-n",
    ns,
    "-o",
    "jsonpath={.data.KEYCLOAK_ADMIN_PASSWORD}",
  ]);
  requireOk(Boolean(kcAdmin), "repody-runtime-secrets missing KEYCLOAK_ADMIN_PASSWORD (Keycloak admin from Vault/ESO)");

  const registryData = ocOut([
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
      const hasInternal = hosts.some((h) => h.includes("image-registry.openshift-image-registry.svc"));
      requireOk(hasInternal, "registry-pull-secret missing internal OpenShift registry auth host");
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
  for (const release of ["repody-data", "repody-auth", "repody"]) {
    const row = releases.find((r) => r.name === release);
    if (!row) {
      warnIf(true, `helm release ${release} not found in ${ns}`);
    } else {
      requireOk(row.status === "deployed", `helm release ${release} status is ${row.status}, expected deployed`);
    }
  }

  const apiReady = ocOut([
    "get",
    "deploy",
    "repody-api",
    "-n",
    ns,
    "-o",
    "jsonpath={.status.readyReplicas}",
  ]);
  requireOk(apiReady === "1", `repody-api ready replicas: ${apiReady || "0"}`);

  const vaultDev = ocOut([
    "get",
    "statefulset",
    "vault",
    "-n",
    "vault",
    "-o",
    "jsonpath={.spec.template.spec.containers[0].env[?(@.name==\"VAULT_DEV_ROOT_TOKEN_ID\")].value}",
  ]);
  warnIf(Boolean(vaultDev), "Vault dev mode detected — acceptable for CRC lab only");

  if (warnings.length) {
    console.warn("\nWarnings:");
    for (const w of warnings) console.warn(`  - ${w}`);
  }

  if (failures.length) {
    console.error("\nClient readiness FAILED:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }

  console.log(`\nClient readiness OK for namespace ${ns}.\n`);
}

main();
