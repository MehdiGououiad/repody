#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { stackFileArgs, HATCHET_INIT_PROFILE } from "../platform-modules.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const registry = (process.env.REPODY_IMAGE_REGISTRY ?? process.env.REGISTRY ?? "")
  .replace(/\/$/, "");
const tag = process.env.REPODY_IMAGE_TAG ?? process.env.TAG ?? "latest";
const push = process.argv.includes("--push");

const fileArgs = stackFileArgs("prod-micro");
const profiles = ["--profile", "web", "--profile", HATCHET_INIT_PROFILE];

function run(args) {
  const result = spawnSync("docker", args, {
    stdio: "inherit",
    cwd: root,
    env: {
      ...process.env,
      REPODY_IMAGE_REGISTRY: registry ? `${registry}/` : "",
      REPODY_IMAGE_TAG: tag,
      AUTH_SECRET: process.env.AUTH_SECRET ?? "build-placeholder-secret-32chars-min",
      AUTH_KEYCLOAK_CLIENT_SECRET:
        process.env.AUTH_KEYCLOAK_CLIENT_SECRET ?? "repody-web-dev-secret",
      AUDIT_MINIO_PUBLIC_ENDPOINT:
        process.env.AUDIT_MINIO_PUBLIC_ENDPOINT ?? "files.example.com",
    },
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

console.log(`Building Repody images (tag=${tag}, registry=${registry || "(local)"})`);
run([
  "compose",
  ...fileArgs,
  ...profiles,
  "build",
  "api",
  "worker",
  "worker-fast",
  "web",
]);

if (push) {
  for (const name of [
    registry ? `${registry}/repody-api:${tag}` : `repody-api:${tag}`,
    registry ? `${registry}/repody-worker:${tag}` : `repody-worker:${tag}`,
    registry ? `${registry}/repody-web:${tag}` : `repody-web:${tag}`,
  ]) {
    console.log(`\n→ push ${name}`);
    run(["push", name]);
  }
}

console.log("\nDone.");
