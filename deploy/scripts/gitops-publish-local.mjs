#!/usr/bin/env node
/**
 * GitOps publish loop for local Harbor + Argo CD (repody-local-* apps):
 *   build → push (Harbor) → bump values-local-images.yaml → commit/push Git → Argo sync
 *
 *   pnpm gitops:publish
 *   pnpm gitops:publish -- --build --push --sync
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { bumpHelmImageTags, readHelmImageTag } from "./bump-helm-image-tags.mjs";
import { gitShortSha } from "./git-sha.mjs";
import { resolveLocalRegistryConfig } from "./k8s-local-registry-config.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const VALUES_LOCAL_IMAGES = path.join(
  root,
  "deploy/helm/repody/values-local-images.yaml",
);
const REGISTRY_CONFIG = resolveLocalRegistryConfig(root);
const HARBOR_REGISTRY = `${REGISTRY_CONFIG.registryHost}:${REGISTRY_CONFIG.harborHttpPort}/${REGISTRY_CONFIG.harborProject}`;

const doBuild = process.argv.includes("--build");
const doPush = process.argv.includes("--push");
const doCommit = process.argv.includes("--commit") || doPush;
const doSync = process.argv.includes("--sync") || doPush;
const doAll = process.argv.includes("--all");

function run(cmd, args, { cwd = root, env = process.env } = {}) {
  const result = spawnSync(cmd, args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
    env,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function capture(cmd, args, { cwd = root } = {}) {
  const result = spawnSync(cmd, args, {
    cwd,
    encoding: "utf8",
    shell: process.platform === "win32",
    env: process.env,
  });
  if (result.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} failed`);
  }
  return result.stdout.trim();
}

function heading(text) {
  console.error(`\n> ${text}\n`);
}

async function main() {
  const imageTag = process.env.REPODY_IMAGE_TAG ?? gitShortSha(root);
  const build = doBuild || doAll;
  const push = doPush || doAll;
  const commit = doCommit || doAll;
  const sync = doSync || doAll;

  heading(`GitOps publish (tag ${imageTag})`);

  if (build) {
    run(
      "node",
      ["deploy/scripts/build-images.mjs"],
      {
        cwd: root,
        env: {
          ...process.env,
          REPODY_IMAGE_TAG: imageTag,
          REPODY_BACKEND_IMAGE_TAG: imageTag,
          REPODY_WEB_IMAGE_TAG: imageTag,
          REPODY_IMAGE_REGISTRY: HARBOR_REGISTRY,
          REGISTRY: HARBOR_REGISTRY,
        },
      },
    );
  }

  if (push) {
    run(
      "node",
      ["deploy/scripts/build-images.mjs", "--push"],
      {
        cwd: root,
        env: {
          ...process.env,
          REPODY_IMAGE_TAG: imageTag,
          REPODY_BACKEND_IMAGE_TAG: imageTag,
          REPODY_WEB_IMAGE_TAG: imageTag,
          REPODY_IMAGE_REGISTRY: HARBOR_REGISTRY,
          REGISTRY: HARBOR_REGISTRY,
        },
      },
    );
  }

  const before = readHelmImageTag(VALUES_LOCAL_IMAGES);
  bumpHelmImageTags(VALUES_LOCAL_IMAGES, imageTag);
  const after = readHelmImageTag(VALUES_LOCAL_IMAGES);
  if (before !== after) {
    console.error(`ok: values-local-images.yaml ${before} → ${after}`);
  } else {
    console.error(`ok: values-local-images.yaml already at ${after}`);
  }

  if (commit) {
    const rel = path
      .relative(root, VALUES_LOCAL_IMAGES)
      .replace(/\\/g, "/");
    run("git", ["add", rel]);
    const staged = spawnSync("git", ["diff", "--cached", "--quiet"], {
      cwd: root,
      shell: false,
    });
    if (staged.status === 1) {
      run("git", [
        "commit",
        "-m",
        `chore(gitops): promote local images to ${imageTag}`,
      ]);
    } else {
      console.error("ok: no commit needed (values-local-images.yaml unchanged)");
    }
  }

  if (push) {
    run("git", ["push"]);
    console.error("ok: pushed Git revision for Argo CD");
  }

  if (sync) {
    if (!push) {
      console.error(
        "… syncing Argo CD against current Git (remote must already include bumped tags)",
      );
    }
    run("node", ["deploy/scripts/gitops-sync-local.mjs"]);
  } else if (!push) {
    console.error(`
Next steps for Argo CD Synced:
  1. git add deploy/helm/repody/values-local-images.yaml
  2. git commit -m "chore(gitops): promote local images to ${imageTag}"
  3. git push
  4. pnpm gitops:sync
`);
  }
}

main().catch((error) => {
  console.error(error?.message || error);
  process.exit(1);
});
