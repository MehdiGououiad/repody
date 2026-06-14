#!/usr/bin/env node
/**
 * Build and optionally push microservice images for cloud / Kubernetes deploy.
 *
 *   REGISTRY=ghcr.io/yourorg/ TAG=1.0.0 pnpm platform:images:build
 *   pnpm platform:images:push
 *
 * Images: audit-api, audit-worker, audit-web
 */

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const registry = (process.env.AUDIT_IMAGE_REGISTRY ?? process.env.REGISTRY ?? "")
  .replace(/\/$/, "");
const tag = process.env.AUDIT_IMAGE_TAG ?? process.env.TAG ?? "latest";
const push = process.argv.includes("--push");

function imageName(role) {
  const base = `${role}:${tag}`;
  return registry ? `${registry}/${base}` : base;
}

/** @param {string[]} args */
function run(args) {
  const result = spawnSync("docker", args, { stdio: "inherit", cwd: root });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

const images = [
  {
    name: imageName("audit-api"),
    build: ["build", "-f", "backend/Dockerfile", "--target", "api", "-t", imageName("audit-api"), "backend"],
  },
  {
    name: imageName("audit-worker"),
    build: ["build", "-f", "backend/Dockerfile", "--target", "worker", "-t", imageName("audit-worker"), "backend"],
  },
  {
    name: imageName("audit-web"),
    build: ["build", "-f", "Dockerfile.web", "-t", imageName("audit-web"), "."],
  },
];

console.log(`Building platform images (tag=${tag}, registry=${registry || "(local)"})`);

for (const img of images) {
  console.log(`\n→ ${img.name}`);
  run(img.build);
  if (push) {
    run(["push", img.name]);
  }
}

console.log("\nDone.");
if (!push) {
  console.log("Push with: pnpm platform:images:push");
}
