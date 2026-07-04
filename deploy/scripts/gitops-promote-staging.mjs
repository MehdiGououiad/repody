#!/usr/bin/env node
/**
 * Bump staging Helm image tags after a release (CI or local).
 * Used by .github/workflows/gitops-promote-staging.yml
 *
 *   node deploy/scripts/gitops-promote-staging.mjs [--commit]
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bumpHelmImageTags } from "./bump-helm-image-tags.mjs";
import { fail, log } from "./lib/cli.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const stagingValues = path.join(root, "deploy/helm/repody/values-staging.yaml");
const tag = (process.env.REPODY_IMAGE_TAG ?? "").trim();

if (!tag) {
  fail("REPODY_IMAGE_TAG is required");
}

bumpHelmImageTags(stagingValues, tag);
log("promote", `Updated ${path.relative(root, stagingValues)} → tag ${tag}`);

if (process.argv.includes("--commit")) {
  const git = process.platform === "win32" ? "git.exe" : "git";
  spawnSync(git, ["add", stagingValues], { cwd: root, stdio: "inherit" });
  const commit = spawnSync(
    git,
    ["commit", "-m", `chore(gitops): promote staging images to ${tag}`],
    { cwd: root, stdio: "inherit" },
  );
  if (commit.status !== 0) {
    process.exit(commit.status ?? 1);
  }
}
