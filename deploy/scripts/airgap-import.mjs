#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";

function parseArgs(argv) {
  let bundle = "";
  let registry = "";
  let verify = true;
  let localOnly = false;
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--bundle") {
      bundle = argv[++i] ?? "";
      if (!bundle || bundle.startsWith("--")) {
        console.error("Missing value for --bundle.");
        usage();
      }
    } else if (arg === "--registry") {
      registry = argv[++i] ?? "";
      if (!registry || registry.startsWith("--")) {
        console.error("Missing value for --registry.");
        usage();
      }
    } else if (arg === "--no-verify") {
      verify = false;
    } else if (arg === "--local-only") {
      localOnly = true;
    } else {
      console.error(`Unknown option: ${arg}`);
      usage();
    }
  }
  if (!bundle) {
    console.error("Missing --bundle.");
    usage();
  }
  if (registry && localOnly) {
    console.error("Use either --registry or --local-only, not both.");
    usage();
  }
  if (!registry && !localOnly) {
    console.error("Missing --registry. Use --local-only only when you intentionally want a local Docker load.");
    usage();
  }
  return { bundle: path.resolve(bundle), registry: registry.replace(/\/$/, ""), verify };
}

function usage() {
  console.error(
    "Usage: pnpm airgap:import -- --bundle DIR --registry registry.example.com/repody [--no-verify]",
  );
  console.error("       pnpm airgap:import -- --bundle DIR --local-only [--no-verify]");
  process.exit(1);
}

function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, { stdio: "inherit", shell: false, ...opts });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function runCapture(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, { encoding: "utf8", shell: false, ...opts });
  if (result.status !== 0) process.exit(result.status ?? 1);
  return result.stdout ?? "";
}

function verifyChecksums(bundleDir) {
  if (!existsSync(path.join(bundleDir, "SHA256SUMS"))) {
    console.error("SHA256SUMS not found.");
    process.exit(1);
  }
  if (process.platform !== "win32") run("sha256sum", ["-c", "SHA256SUMS"], { cwd: bundleDir });
}

function importImages(bundleDir, registry) {
  const imagesDir = path.join(bundleDir, "images");
  if (!existsSync(imagesDir)) {
    console.error(`Missing ${imagesDir}`);
    process.exit(1);
  }
  for (const file of readdirSync(imagesDir).filter((f) => f.endsWith(".tar"))) {
    const loaded = runCapture("docker", ["load", "-i", path.join(imagesDir, file)]);
    if (!registry) continue;
    const refs = [...loaded.matchAll(/Loaded image: (.+)/g)].map((m) => m[1].trim());
    for (const imageRef of refs) {
      const base = imageRef.includes("/") ? imageRef.split("/").pop() : imageRef;
      const target = `${registry}/${base}`;
      run("docker", ["tag", imageRef, target]);
      run("docker", ["push", target]);
    }
  }
}

const { bundle, registry, verify } = parseArgs(process.argv);
if (!existsSync(bundle)) {
  console.error(`Bundle not found: ${bundle}`);
  process.exit(1);
}
const releasePath = path.join(bundle, "RELEASE.json");
if (existsSync(releasePath)) {
  const release = JSON.parse(readFileSync(releasePath, "utf8"));
  console.log(`Importing ${release.name} ${release.version}`);
}
if (verify) verifyChecksums(bundle);
importImages(bundle, registry);
console.log("Import complete. Deploy with Helm and configure external inference in my-values.yaml.");
