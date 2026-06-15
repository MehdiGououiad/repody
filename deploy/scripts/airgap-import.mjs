#!/usr/bin/env node
/**
 * Import an air-gap release into a private OCI registry (regulated zone or staging).
 *
 * Usage:
 *   node deploy/scripts/airgap-import.mjs --bundle dist/airgap/repody-airgap-0.1.0 --registry registry.internal.example.com/repody
 *
 * Without --registry: docker load only (local daemon).
 */
import { spawnSync } from "node:child_process";
import {
  existsSync,
  readFileSync,
  readdirSync,
} from "node:fs";
import path from "node:path";

function parseArgs(argv) {
  let bundle = "";
  let registry = "";
  let verify = true;
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--bundle") bundle = argv[++i] ?? "";
    else if (arg === "--registry") registry = argv[++i] ?? "";
    else if (arg === "--no-verify") verify = false;
    else if (arg === "--help" || arg === "-h") {
      console.log(
        "Usage: airgap-import.mjs --bundle <dir> [--registry host/path] [--no-verify]"
      );
      process.exit(0);
    }
  }
  if (!bundle) {
    console.error("Missing --bundle (extracted repody-airgap-X.Y.Z directory).");
    process.exit(1);
  }
  return {
    bundle: path.resolve(bundle),
    registry: registry.replace(/\/$/, ""),
    verify,
  };
}

function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: process.platform === "win32",
    ...opts,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function runCapture(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, {
    encoding: "utf8",
    shell: process.platform === "win32",
    ...opts,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
  return result.stdout ?? "";
}

function verifyChecksums(bundleDir) {
  const sumsPath = path.join(bundleDir, "SHA256SUMS");
  if (!existsSync(sumsPath)) {
    console.error("SHA256SUMS not found — refusing import.");
    process.exit(1);
  }
  if (process.platform === "win32") {
    console.warn("Checksum verification on Windows: verify SHA256SUMS manually or use WSL/Linux.");
    return;
  }
  run("sha256sum", ["-c", "SHA256SUMS"], { cwd: bundleDir });
}

/** @param {string} bundleDir @param {string} registry */
function importImages(bundleDir, registry) {
  const imagesDir = path.join(bundleDir, "images");
  if (!existsSync(imagesDir)) {
    console.error(`Missing ${imagesDir}`);
    process.exit(1);
  }

  for (const file of readdirSync(imagesDir).filter((f) => f.endsWith(".tar"))) {
    const archive = path.join(imagesDir, file);
    console.log(`\n→ load ${file}`);
    const loaded = runCapture("docker", ["load", "-i", archive]);
    if (!registry) continue;

    const refs = [...loaded.matchAll(/Loaded image: (.+)/g)].map((m) => m[1].trim());
    for (const imageRef of refs) {
      const base = imageRef.includes("/") ? imageRef.split("/").pop() : imageRef;
      const target = `${registry}/${base}`;
      console.log(`  push ${imageRef} → ${target}`);
      run("docker", ["tag", imageRef, target]);
      run("docker", ["push", target]);
    }
  }
}

function main() {
  const { bundle, registry, verify } = parseArgs(process.argv);
  if (!existsSync(bundle)) {
    console.error(`Bundle not found: ${bundle}`);
    process.exit(1);
  }

  const releasePath = path.join(bundle, "RELEASE.json");
  if (existsSync(releasePath)) {
    const release = JSON.parse(readFileSync(releasePath, "utf8"));
    console.log(`Importing ${release.name} ${release.version} (modules: ${release.modules?.join(", ")})`);
  }

  if (verify) {
    console.log("\n▶ Verifying SHA256SUMS");
    verifyChecksums(bundle);
  }

  console.log("\n▶ Loading container images");
  importImages(bundle, registry);

  const modelInfo = path.join(bundle, "models", "MODEL_INFO.json");
  const modelTar = path.join(bundle, "models", "repody-vlm-model.tar");
  if (existsSync(modelTar)) {
    console.log("\n▶ Loading Repody VLM model archive");
    run("docker", ["load", "-i", modelTar]);
  } else if (existsSync(modelInfo)) {
    console.log("\n▶ Model bundle requires Docker Model Runner import — see models/MODEL_INFO.json");
  }

  console.log("\n✓ Import complete.");
  if (registry) {
    console.log(`  Set REPODY_IMAGE_REGISTRY=${registry}/ and REPODY_IMAGE_TAG from RELEASE.json`);
  }
  console.log("  Compose: see docs/AIRGAP.md");
  console.log("  Helm: helm upgrade --install repody <bundle>/charts/repody-*.tgz -f my-values.yaml");
}

main();
