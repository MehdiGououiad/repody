#!/usr/bin/env node
/**
 * Build a versioned air-gap release on connected Linux CI (images + helm + model + checksums).
 * No secrets are written into the bundle.
 *
 * Usage:
 *   node deploy/scripts/airgap-build-release.mjs --version 0.1.0
 *   node deploy/scripts/airgap-build-release.mjs --version 0.1.0 --output dist/airgap
 */
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AIRGAP_MODEL,
  airgapImageManifest,
  imageArchiveName,
} from "../airgap/manifest.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function parseArgs(argv) {
  let version = process.env.REPODY_AIRGAP_VERSION ?? "";
  let output = "";
  let skipModel = false;
  let skipHelm = false;
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--version") version = argv[++i] ?? "";
    else if (arg === "--output") output = argv[++i] ?? "";
    else if (arg === "--skip-model") skipModel = true;
    else if (arg === "--skip-helm") skipHelm = true;
    else if (arg === "--help" || arg === "-h") {
      console.log(`Usage: airgap-build-release.mjs --version X.Y.Z [--output dir] [--skip-model] [--skip-helm]`);
      process.exit(0);
    }
  }
  if (!version) {
    console.error("Missing --version (or REPODY_AIRGAP_VERSION).");
    process.exit(1);
  }
  const bundleRoot =
    output ||
    path.join(root, "dist", "airgap", `repody-airgap-${version}`);
  return { version, bundleRoot, skipModel, skipHelm };
}

function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    cwd: root,
    shell: process.platform === "win32",
    ...opts,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function runCapture(cmd, args) {
  const result = spawnSync(cmd, args, {
    encoding: "utf8",
    cwd: root,
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    console.error(result.stderr || result.stdout);
    process.exit(result.status ?? 1);
  }
  return result.stdout;
}

/** @param {string} filePath */
function sha256File(filePath) {
  const hash = createHash("sha256");
  const data = readFileSync(filePath);
  hash.update(data);
  return hash.digest("hex");
}

/** @param {string} dir */
function writeSha256Sums(dir) {
  const lines = [];
  function walk(rel = "") {
    const abs = path.join(dir, rel);
    for (const name of readdirSync(abs)) {
      const childRel = rel ? `${rel}/${name}` : name;
      if (name === "SHA256SUMS") continue;
      const childAbs = path.join(abs, name);
      const st = statSync(childAbs);
      if (st.isDirectory()) walk(childRel);
      else lines.push(`${sha256File(childAbs)}  ${childRel.replace(/\\/g, "/")}`);
    }
  }
  walk();
  lines.sort();
  writeFileSync(path.join(dir, "SHA256SUMS"), `${lines.join("\n")}\n`, "utf8");
}

function main() {
  if (process.platform === "win32") {
    console.error("Build air-gap releases on Linux CI (connected staging). Import works on Linux.");
    process.exit(1);
  }

  const { version, bundleRoot, skipModel, skipHelm } = parseArgs(process.argv);
  const tag = version;
  const manifest = airgapImageManifest({ tag });

  mkdirSync(bundleRoot, { recursive: true });
  const imagesDir = path.join(bundleRoot, "images");
  const modelsDir = path.join(bundleRoot, "models");
  const chartsDir = path.join(bundleRoot, "charts");
  const deployDir = path.join(bundleRoot, "deploy");
  mkdirSync(imagesDir, { recursive: true });
  mkdirSync(modelsDir, { recursive: true });
  mkdirSync(chartsDir, { recursive: true });
  mkdirSync(deployDir, { recursive: true });

  console.log(`\n▶ Building Repody app images (tag=${tag})`);
  run("node", ["deploy/scripts/build-images.mjs"], {
    env: {
      ...process.env,
      REPODY_IMAGE_TAG: tag,
      REPODY_IMAGE_REGISTRY: "",
      AUTH_SECRET: process.env.AUTH_SECRET ?? "airgap-build-placeholder-secret",
      AUDIT_MINIO_PUBLIC_ENDPOINT:
        process.env.AUDIT_MINIO_PUBLIC_ENDPOINT ?? "files.example.com",
      NEXT_PUBLIC_BUGSINK_DSN: process.env.NEXT_PUBLIC_BUGSINK_DSN ?? "",
      BUGSINK_DSN: process.env.BUGSINK_DSN ?? "",
    },
  });

  console.log("\n▶ Pulling and exporting third-party images");
  for (const imageRef of manifest.upstream) {
    console.log(`  → ${imageRef}`);
    run("docker", ["pull", imageRef]);
    const out = path.join(imagesDir, imageArchiveName(imageRef));
    run("docker", ["save", "-o", out, imageRef]);
  }

  console.log("\n▶ Exporting Repody app images");
  for (const imageRef of manifest.app) {
    console.log(`  → ${imageRef}`);
    const out = path.join(imagesDir, imageArchiveName(imageRef));
    run("docker", ["save", "-o", out, imageRef]);
  }

  if (!skipModel) {
    console.log("\n▶ Exporting Repody VLM model (Docker Model Runner)");
    run("bash", ["deploy/airgap/export-repody-vlm-model.sh", modelsDir]);
  }

  if (!skipHelm) {
    console.log("\n▶ Packaging Helm chart");
    run("node", ["scripts/helm-deps.mjs"]);
    run("helm", ["package", "deploy/helm/repody", "-d", chartsDir]);
  }

  const chartPkgs = existsSync(chartsDir)
    ? readdirSync(chartsDir).filter((f) => f.startsWith("repody-") && f.endsWith(".tgz"))
    : [];

  console.log("\n▶ Copying deploy manifests");
  cpSync(path.join(root, "deploy/compose"), path.join(deployDir, "compose"), {
    recursive: true,
  });
  cpSync(path.join(root, "deploy/pinned-images.env"), path.join(deployDir, "pinned-images.env"));
  copyFileSync(
    path.join(root, "deploy/platform-modules.mjs"),
    path.join(deployDir, "platform-modules.mjs")
  );
  copyFileSync(
    path.join(root, "deploy/compose-paths.mjs"),
    path.join(deployDir, "compose-paths.mjs")
  );

  const release = {
    name: "repody-airgap",
    version,
    builtAt: new Date().toISOString(),
    gitSha: process.env.GITHUB_SHA ?? null,
    modules: manifest.modules,
    inference: "docker-model-runner",
    imageTag: tag,
    images: {
      upstream: manifest.upstream,
      app: manifest.app,
    },
    model: skipModel ? null : AIRGAP_MODEL,
    helmChart: skipHelm ? null : chartPkgs[0] ? `charts/${chartPkgs[0]}` : null,
    secretsInBundle: false,
  };
  writeFileSync(
    path.join(bundleRoot, "RELEASE.json"),
    `${JSON.stringify(release, null, 2)}\n`,
    "utf8"
  );
  writeFileSync(
    path.join(bundleRoot, "MANIFEST.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8"
  );

  writeSha256Sums(bundleRoot);

  const archivePath = `${bundleRoot}.tar.gz`;
  console.log(`\n▶ Creating ${archivePath}`);
  run("tar", ["-czf", archivePath, "-C", path.dirname(bundleRoot), path.basename(bundleRoot)]);

  console.log(`\n✓ Air-gap release ready: ${bundleRoot}`);
  console.log(`  Archive: ${archivePath}`);
  console.log(`  Verify: sha256sum -c SHA256SUMS  (inside bundle dir)`);
}

main();
