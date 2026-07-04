#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const args = process.argv.slice(2);

function valuesFor(flag) {
  const values = [];
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === flag && args[i + 1]) {
      values.push(args[i + 1]);
      i += 1;
    }
  }
  return values;
}

function valueFor(flag, fallback) {
  const values = valuesFor(flag);
  return values.length > 0 ? values[values.length - 1] : fallback;
}

const allowPlaceholders = args.includes("--allow-placeholders");
const requireVlmApiKey = args.includes("--require-vlm-api-key");
const valuesFiles = valuesFor("--values");
const externalSecretFile = valueFor(
  "--external-secret",
  "deploy/managed/external-secrets/repody-runtime-externalsecret.example.yaml",
);
const clusterSecretStoreFile = valueFor(
  "--cluster-secret-store",
  "deploy/managed/external-secrets/vault-clustersecretstore.example.yaml",
);

if (valuesFiles.length === 0) {
  valuesFiles.push(
    "deploy/helm/repody/values-production.yaml.example",
    "deploy/helm/repody/values-production.onprem-managed.yaml.example",
  );
}

function read(path) {
  return readFileSync(resolve(path), "utf8");
}

function section(text, name) {
  const pattern = new RegExp(`^${name}:\\r?\\n([\\s\\S]*?)(?=^\\S|\\z)`, "gm");
  const matches = Array.from(text.matchAll(pattern));
  if (matches.length === 0) return "";
  if (matches.length === 1) return matches[0][1];

  const merged = new Map();
  for (const match of matches) {
    for (const line of match[1].split(/\r?\n/)) {
      const keyMatch = line.match(/^(\s*)([A-Za-z0-9_.]+):\s*(.*)$/);
      if (keyMatch) merged.set(keyMatch[2], line);
    }
  }
  return `${Array.from(merged.values()).join("\n")}\n`;
}

function hasLine(text, key, value) {
  const escaped = String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`^\\s*${key}:\\s*${escaped}\\s*$`, "m").test(text);
}

function collectSecretKeys(externalSecretText) {
  return new Set(
    Array.from(externalSecretText.matchAll(/^\s*-\s*secretKey:\s*([A-Z0-9_]+)/gm), (match) => match[1]),
  );
}

const valuesText = valuesFiles.map(read).join("\n");
const externalSecretText = read(externalSecretFile);
const clusterSecretStoreText = read(clusterSecretStoreFile);
const failures = [];
const warnings = [];

function requireCondition(condition, message) {
  if (!condition) failures.push(message);
}

requireCondition(
  hasLine(section(valuesText, "global"), "deploymentEnvironment", "production"),
  "values must set global.deploymentEnvironment: production",
);
requireCondition(
  hasLine(section(valuesText, "secrets"), "create", "false"),
  "values must set secrets.create: false",
);
requireCondition(
  hasLine(section(valuesText, "secrets"), "existingSecret", "repody-runtime-secrets"),
  "values must set secrets.existingSecret: repody-runtime-secrets",
);

for (const [name, requiredLines] of [
  ["externalDatabase", [["enabled", "true"], ["existingSecret", "repody-runtime-secrets"], ["urlKey", "AUDIT_DATABASE_URL"]]],
  ["externalRedis", [["enabled", "true"], ["existingSecret", "repody-runtime-secrets"], ["urlKey", "AUDIT_REDIS_URL"]]],
  [
    "externalObjectStorage",
    [
      ["enabled", "true"],
      ["existingSecret", "repody-runtime-secrets"],
      ["accessKeyKey", "AUDIT_MINIO_ACCESS_KEY"],
      ["secretKeyKey", "AUDIT_MINIO_SECRET_KEY"],
    ],
  ],
]) {
  const block = section(valuesText, name);
  requireCondition(block.length > 0, `values must include ${name}`);
  for (const [key, value] of requiredLines) {
    requireCondition(hasLine(block, key, value), `values ${name}.${key} must be ${value}`);
  }
}

requireCondition(
  !/^\s*(accessKey|secretKey|url):\s*['"]?\S+/m.test(section(valuesText, "externalObjectStorage")),
  "production values must not include inline externalObjectStorage accessKey/secretKey/url secrets",
);

const requiredKeys = [
  "AUTH_SECRET",
  "AUTH_KEYCLOAK_CLIENT_SECRET",
  "AUDIT_DATABASE_URL",
  "AUDIT_REDIS_URL",
  "AUDIT_MINIO_ACCESS_KEY",
  "AUDIT_MINIO_SECRET_KEY",
  "BUGSINK_DSN",
];
if (requireVlmApiKey) requiredKeys.push("AUDIT_VLLM_API_KEY");

const externalSecretKeys = collectSecretKeys(externalSecretText);
for (const key of requiredKeys) {
  requireCondition(externalSecretKeys.has(key), `ExternalSecret must map ${key}`);
}

if (!externalSecretKeys.has("AUDIT_VLLM_API_KEY")) {
  warnings.push("ExternalSecret does not map AUDIT_VLLM_API_KEY; OK only when the external VLM endpoint has no bearer token.");
}

requireCondition(
  /kind:\s*ExternalSecret/.test(externalSecretText),
  "runtime secret manifest must be an ExternalSecret",
);
requireCondition(
  /name:\s*repody-runtime-secrets/.test(externalSecretText),
  "ExternalSecret target/name must produce repody-runtime-secrets",
);
requireCondition(
  /kind:\s*ClusterSecretStore/.test(clusterSecretStoreText),
  "secret store manifest must define a ClusterSecretStore",
);
requireCondition(
  /auth:\s*\n\s*kubernetes:/.test(clusterSecretStoreText),
  "Vault ClusterSecretStore should use Kubernetes auth for workload identity",
);

if (!allowPlaceholders) {
  const placeholderPattern = /(YOUR_ORG|yourdomain\.com|example\.com|CHANGE_ME|<[^>]+>|replace-with|0\.1\.0)/;
  for (const [label, text] of [
    ["values", valuesText],
    ["ExternalSecret", externalSecretText],
    ["ClusterSecretStore", clusterSecretStoreText],
  ]) {
    requireCondition(!placeholderPattern.test(text), `${label} still contains example placeholders`);
  }
}

for (const warning of warnings) {
  console.warn(`warning: ${warning}`);
}

if (failures.length > 0) {
  console.error("enterprise secret preflight failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("enterprise secret preflight passed");
