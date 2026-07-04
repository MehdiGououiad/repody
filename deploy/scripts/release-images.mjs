#!/usr/bin/env node
/**
 * Shared image coordinates for release, SBOM, and cosign flows.
 */
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

export function resolveRegistry() {
  return (process.env.REPODY_IMAGE_REGISTRY ?? process.env.REGISTRY ?? "").replace(/\/$/, "");
}

export function resolveTag() {
  return (
    process.env.REPODY_IMAGE_TAG ??
    process.env.TAG ??
    process.env.REPODY_BACKEND_IMAGE_TAG ??
    process.env.REPODY_WEB_IMAGE_TAG ??
    "latest"
  );
}

export function resolveBackendTag() {
  return process.env.REPODY_BACKEND_IMAGE_TAG ?? process.env.REPODY_IMAGE_TAG ?? process.env.TAG ?? "latest";
}

export function resolveWebTag() {
  return (
    process.env.REPODY_WEB_IMAGE_TAG ??
    process.env.REPODY_IMAGE_TAG ??
    process.env.TAG ??
    resolveBackendTag()
  );
}

/** @param {string} name @param {string} tag */
export function imageRef(name, tag, registry = resolveRegistry()) {
  return registry ? `${registry}/${name}:${tag}` : `${name}:${tag}`;
}

export function releaseImageSet(options = {}) {
  const registry = options.registry ?? resolveRegistry();
  const backendTag = options.backendTag ?? resolveBackendTag();
  const webTag = options.webTag ?? resolveWebTag();
  return [
    { role: "backend", name: "repody-backend", tag: backendTag, ref: imageRef("repody-backend", backendTag, registry) },
    { role: "web", name: "repody-web", tag: webTag, ref: imageRef("repody-web", webTag, registry) },
  ];
}

export function gitSha() {
  const result = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd: root,
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) return process.env.GITHUB_SHA ?? "unknown";
  return result.stdout.trim();
}

export function gitTagAtHead() {
  const result = spawnSync("git", ["describe", "--tags", "--exact-match"], {
    cwd: root,
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) return null;
  return result.stdout.trim();
}

/** @param {string} imageRef */
export function resolveDigest(imageRef) {
  const result = spawnSync(
    "docker",
    ["buildx", "imagetools", "inspect", imageRef, "--format", "{{json .}}"],
    { encoding: "utf8", shell: false },
  );
  if (result.status !== 0) {
    throw new Error(`Could not resolve digest for ${imageRef}: ${(result.stderr ?? "").trim()}`);
  }
  try {
    const payload = JSON.parse(result.stdout);
    const digest = payload?.manifest?.digest ?? payload?.Descriptor?.digest;
    if (!digest) throw new Error("digest missing in inspect output");
    return digest;
  } catch (error) {
    throw new Error(`Invalid digest response for ${imageRef}: ${error instanceof Error ? error.message : error}`);
  }
}

export function helmImagesYaml(images, indent = "  ") {
  const backend = images.find((i) => i.role === "backend");
  const web = images.find((i) => i.role === "web");
  if (!backend || !web) throw new Error("release image set incomplete");
  const repo = (ref) => ref.slice(0, ref.lastIndexOf(":"));
  return `images:
${indent}backend:
${indent}  repository: ${repo(backend.ref)}
${indent}  tag: "${backend.tag}"
${indent}  digest: "${backend.digest ?? ""}"
${indent}api:
${indent}  repository: ${repo(backend.ref)}
${indent}  tag: "${backend.tag}"
${indent}  digest: "${backend.digest ?? ""}"
${indent}worker:
${indent}  repository: ${repo(backend.ref)}
${indent}  tag: "${backend.tag}"
${indent}  digest: "${backend.digest ?? ""}"
${indent}web:
${indent}  repository: ${repo(web.ref)}
${indent}  tag: "${web.tag}"
${indent}  digest: "${web.digest ?? ""}"
`;
}

export function readPackageVersion() {
  try {
    const pkg = JSON.parse(readFileSync(path.join(root, "package.json"), "utf8"));
    return pkg.version ?? "0.0.0";
  } catch {
    return "0.0.0";
  }
}
