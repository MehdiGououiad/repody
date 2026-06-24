#!/usr/bin/env node
/**
 * Copy cross-namespace platform secrets into repody-app (Hatchet client token).
 */
import { spawnSync } from "node:child_process";

const SRC_NS = process.env.REPODY_QUEUE_NAMESPACE ?? "repody-queue";
const DST_NS = process.env.REPODY_APP_NAMESPACE ?? "repody-app";
const SECRET = "hatchet-client-config";

function capture(cmd, args) {
  const result = spawnSync(cmd, args, {
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) {
    return null;
  }
  return result.stdout.trim();
}

function applySecretCopy() {
  const raw = capture("kubectl", [
    "-n",
    SRC_NS,
    "get",
    `secret/${SECRET}`,
    "-o",
    "json",
  ]);
  if (!raw) {
    console.error(`skip: ${SRC_NS}/${SECRET} not found yet`);
    return false;
  }

  const secret = JSON.parse(raw);
  const token = secret.data?.HATCHET_CLIENT_TOKEN;
  if (!token) {
    console.error(`skip: ${SRC_NS}/${SECRET} has no HATCHET_CLIENT_TOKEN yet`);
    return false;
  }

  delete secret.metadata.resourceVersion;
  delete secret.metadata.uid;
  delete secret.metadata.creationTimestamp;
  delete secret.metadata.managedFields;
  delete secret.metadata.ownerReferences;
  secret.metadata.namespace = DST_NS;

  const result = spawnSync("kubectl", ["apply", "-f", "-"], {
    input: JSON.stringify(secret),
    encoding: "utf8",
    shell: false,
    stdio: ["pipe", "inherit", "inherit"],
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }

  console.error(`ok: synced ${SECRET} ${SRC_NS} → ${DST_NS}`);
  return true;
}

applySecretCopy();
