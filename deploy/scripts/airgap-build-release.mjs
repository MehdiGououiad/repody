#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
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
import { airgapImageManifest, imageArchiveName } from "../airgap/manifest.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function parseArgs(argv) {
  let version = process.env.REPODY_AIRGAP_VERSION ?? "";
  let output = "";
  let skipHelm = false;
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--version") {
      version = argv[++i] ?? "";
      if (!version || version.startsWith("--")) {
        console.error("Missing value for --version.");
        process.exit(1);
      }
    } else if (arg === "--output") {
      output = argv[++i] ?? "";
      if (!output || output.startsWith("--")) {
        console.error("Missing value for --output.");
        process.exit(1);
      }
    } else if (arg === "--skip-helm") {
      skipHelm = true;
    } else {
      console.error(`Unknown option: ${arg}`);
      console.error("Usage: pnpm airgap:build -- --version X.Y.Z [--output DIR] [--skip-helm]");
      process.exit(1);
    }
  }
  if (!version) {
    console.error("Missing --version.");
    console.error("Usage: pnpm airgap:build -- --version X.Y.Z [--output DIR] [--skip-helm]");
    process.exit(1);
  }
  return {
    version,
    bundleRoot: output || path.join(root, "dist", "airgap", `repody-airgap-${version}`),
    skipHelm,
  };
}

function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    cwd: root,
    shell: false,
    ...opts,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function sha256File(filePath) {
  const hash = createHash("sha256");
  hash.update(readFileSync(filePath));
  return hash.digest("hex");
}

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

const { version, bundleRoot, skipHelm } = parseArgs(process.argv);

if (process.platform === "win32") {
  console.error("Build air-gap releases on Linux CI.");
  process.exit(1);
}

const tag = version;
const manifest = airgapImageManifest({ tag });

mkdirSync(bundleRoot, { recursive: true });
const imagesDir = path.join(bundleRoot, "images");
const chartsDir = path.join(bundleRoot, "charts");
const deployDir = path.join(bundleRoot, "deploy");
mkdirSync(imagesDir, { recursive: true });
mkdirSync(chartsDir, { recursive: true });
mkdirSync(deployDir, { recursive: true });

run("node", ["deploy/scripts/build-images.mjs"], {
  env: { ...process.env, REPODY_IMAGE_TAG: tag, REPODY_IMAGE_REGISTRY: "" },
});

for (const imageRef of manifest.upstream) {
  run("docker", ["pull", imageRef]);
  run("docker", ["save", "-o", path.join(imagesDir, imageArchiveName(imageRef)), imageRef]);
}

for (const imageRef of manifest.app) {
  run("docker", ["save", "-o", path.join(imagesDir, imageArchiveName(imageRef)), imageRef]);
}

if (!skipHelm) {
  run("node", ["scripts/helm-deps.mjs"]);
  run("helm", ["package", "deploy/helm/repody", "-d", chartsDir]);
}

const chartPkgs = existsSync(chartsDir)
  ? readdirSync(chartsDir).filter((f) => f.startsWith("repody-") && f.endsWith(".tgz"))
  : [];

copyFileSync(path.join(root, "deploy/pinned-images.env"), path.join(deployDir, "pinned-images.env"));

const release = {
  name: "repody-airgap",
  version,
  builtAt: new Date().toISOString(),
  gitSha: process.env.GITHUB_SHA ?? null,
  modules: manifest.modules,
  inference: "external-openai-compatible",
  imageTag: tag,
  images: { upstream: manifest.upstream, app: manifest.app },
  model: null,
  helmChart: skipHelm ? null : chartPkgs[0] ? `charts/${chartPkgs[0]}` : null,
  secretsInBundle: false,
};
writeFileSync(path.join(bundleRoot, "RELEASE.json"), `${JSON.stringify(release, null, 2)}\n`, "utf8");
writeFileSync(path.join(bundleRoot, "MANIFEST.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
writeSha256Sums(bundleRoot);

const archivePath = `${bundleRoot}.tar.gz`;
run("tar", ["-czf", archivePath, "-C", path.dirname(bundleRoot), path.basename(bundleRoot)]);
console.log(`Air-gap release ready: ${archivePath}`);
