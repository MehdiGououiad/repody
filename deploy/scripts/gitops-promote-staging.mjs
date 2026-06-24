#!/usr/bin/env node
/**
 * Promote immutable image tags into Git for staging Argo CD.
 * https://argo-cd.readthedocs.io/en/stable/user-guide/ci_automation/
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { bumpHelmImageTags, readHelmImageTag } from "./bump-helm-image-tags.mjs";
import { gitShortSha } from "./git-sha.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const VALUES_STAGING_IMAGES = path.join(
  root,
  "deploy/helm/repody/values-staging-images.yaml",
);

const doCommit = process.argv.includes("--commit");
const imageTag = process.env.REPODY_IMAGE_TAG ?? gitShortSha(root);

function run(cmd, args) {
  const result = spawnSync(cmd, args, {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function capture(cmd, args) {
  const result = spawnSync(cmd, args, {
    cwd: root,
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} failed`);
  }
  return result.stdout.trim();
}

const before = readHelmImageTag(VALUES_STAGING_IMAGES);
bumpHelmImageTags(VALUES_STAGING_IMAGES, imageTag);
const after = readHelmImageTag(VALUES_STAGING_IMAGES);
console.error(`ok: values-staging-images.yaml ${before} → ${after}`);

if (!doCommit) {
  console.error("dry-run: pass --commit to stage and commit the promotion");
  process.exit(0);
}

const rel = path.relative(root, VALUES_STAGING_IMAGES).replace(/\\/g, "/");
run("git", ["add", rel]);
const staged = spawnSync("git", ["diff", "--cached", "--quiet"], {
  cwd: root,
  shell: false,
});
if (staged.status === 1) {
  run("git", [
    "commit",
    "-m",
    `chore(gitops): promote staging images to ${imageTag}`,
  ]);
  console.error("ok: committed staging image promotion");
} else {
  console.error("ok: no commit needed (values-staging-images.yaml unchanged)");
}

const branch = capture("git", ["rev-parse", "--abbrev-ref", "HEAD"]);
console.error(`next: git push origin ${branch} — Argo CD repody-staging will sync`);
