#!/usr/bin/env node
/**
 * Release supply chain: SPDX SBOM (syft) + cosign sign/verify + promotion manifest.
 *
 *   node deploy/scripts/release-supply-chain.mjs attest|verify|manifest|promote [--check]
 *
 * Env:
 *   REPODY_IMAGE_REGISTRY, REPODY_IMAGE_TAG (or per-image tags)
 *   COSIGN_KEY — optional private key path (on-prem registry). Omit for keyless (GitHub OIDC).
 *   COSIGN_PASSWORD — key password when using COSIGN_KEY
 *   COSIGN_CERTIFICATE_IDENTITY — verify identity (default: GitHub workflow for this repo)
 *   COSIGN_CERTIFICATE_OIDC_ISSUER — default https://token.actions.githubusercontent.com
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  gitSha,
  gitTagAtHead,
  helmImagesYaml,
  readPackageVersion,
  releaseImageSet,
  resolveDigest,
  resolveRegistry,
  resolveTag,
} from "./release-images.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function parseArgs(argv) {
  const flags = new Set();
  const positionals = [];
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--check") flags.add("check");
    else if (arg === "--skip-cosign") flags.add("skip-cosign");
    else if (arg === "--skip-sbom") flags.add("skip-sbom");
    else if (arg === "--skip-digest") flags.add("skip-digest");
    else if (arg === "--dry-run") flags.add("dry-run");
    else if (arg.startsWith("--channel=")) flags.add(`channel:${arg.slice("--channel=".length)}`);
    else if (arg === "--channel") flags.add(`channel:${argv[++i] ?? "staging"}`);
    else if (arg.startsWith("--")) {
      console.error(`Unknown option: ${arg}`);
      process.exit(1);
    } else positionals.push(arg);
  }
  const cmd = positionals[0] ?? "verify";
  const channel = [...flags].find((f) => f.startsWith("channel:"))?.slice("channel:".length) ?? "staging";
  return { cmd, flags, channel };
}

function toolPath(name) {
  const win = process.platform === "win32";
  const probe = spawnSync(win ? "where.exe" : "which", [name], { encoding: "utf8", shell: false });
  if (probe.status !== 0) return null;
  const line = probe.stdout.split(/\r?\n/).find((l) => l.trim());
  return line?.trim() ?? null;
}

function run(cmd, args, { dryRun = false, quiet = false } = {}) {
  if (dryRun) {
    console.log(`[dry-run] ${cmd} ${args.join(" ")}`);
    return { status: 0, stdout: "", stderr: "" };
  }
  const result = spawnSync(cmd, args, {
    cwd: root,
    encoding: "utf8",
    stdio: quiet ? "pipe" : "inherit",
    shell: false,
    env: process.env,
  });
  if (result.status !== 0 && quiet) {
    console.error((result.stderr ?? result.stdout ?? "").trim());
  }
  return result;
}

function sha256File(filePath) {
  const hash = createHash("sha256");
  hash.update(readFileSync(filePath));
  return hash.digest("hex");
}

function releaseDir(tag) {
  const dir = path.join(root, "dist", "release", tag.replace(/[^a-zA-Z0-9._-]/g, "_"));
  mkdirSync(dir, { recursive: true });
  return dir;
}

function sbomPath(dir, name) {
  return path.join(dir, "sbom", `${name}.spdx.json`);
}

function cosignBaseArgs() {
  const key = process.env.COSIGN_KEY?.trim();
  if (key) return ["--key", key];
  return ["--yes"];
}

function defaultCertificateIdentity() {
  if (process.env.COSIGN_CERTIFICATE_IDENTITY?.trim()) {
    return process.env.COSIGN_CERTIFICATE_IDENTITY.trim();
  }
  const repo = process.env.GITHUB_REPOSITORY ?? "MehdiGououiad/repody";
  return `https://github.com/${repo}/.github/workflows/images-ghcr.yml@.*`;
}

function defaultOidcIssuer() {
  return process.env.COSIGN_CERTIFICATE_OIDC_ISSUER?.trim() ?? "https://token.actions.githubusercontent.com";
}

function requireRegistry() {
  const registry = resolveRegistry();
  if (!registry) {
    console.error("REPODY_IMAGE_REGISTRY is required.");
    process.exit(1);
  }
  return registry;
}

async function enrichWithDigests(images, flags) {
  if (flags.has("skip-digest")) return images;
  const out = [];
  for (const image of images) {
    try {
      const digest = resolveDigest(image.ref);
      out.push({ ...image, digest, refAtDigest: `${image.ref.split(":")[0]}@${digest}` });
    } catch (error) {
      if (flags.has("skip-cosign") && flags.has("skip-sbom")) {
        out.push({ ...image, digest: null, refAtDigest: image.ref });
        console.warn(`warn: digest lookup failed for ${image.ref} — continuing`);
      } else {
        throw error;
      }
    }
  }
  return out;
}

function attest(images, flags) {
  requireRegistry();
  const tag = resolveTag();
  const dir = releaseDir(tag);
  mkdirSync(path.join(dir, "sbom"), { recursive: true });

  const syft = toolPath("syft");
  const cosign = toolPath("cosign");
  if (!flags.has("skip-sbom") && !syft) {
    console.error("syft not found. Install: https://github.com/anchore/syft#installation");
    process.exit(1);
  }
  if (!flags.has("skip-cosign") && !cosign) {
    console.error("cosign not found. Install: https://docs.sigstore.dev/cosign/system_install/");
    process.exit(1);
  }

  const dryRun = flags.has("dry-run");
  const signed = [];

  for (const image of images) {
    const target = image.refAtDigest ?? image.ref;
    const sbomOut = sbomPath(dir, image.name);

    if (!flags.has("skip-sbom")) {
      console.log(`\nSBOM ${image.ref}`);
      const syftArgs = ["scan", image.ref, "-o", `spdx-json=${sbomOut}`];
      const syftResult = run(syft, syftArgs, { dryRun });
      if (syftResult.status !== 0) process.exit(syftResult.status ?? 1);
      if (!dryRun && existsSync(sbomOut)) {
        console.log(`  wrote ${path.relative(root, sbomOut)} (${sha256File(sbomOut).slice(0, 12)}…)`);
      }
    }

    if (!flags.has("skip-cosign")) {
      console.log(`\nSign ${target}`);
      const signArgs = ["sign", ...cosignBaseArgs(), target];
      const signResult = run(cosign, signArgs, { dryRun });
      if (signResult.status !== 0) process.exit(signResult.status ?? 1);

      if (!flags.has("skip-sbom") && existsSync(sbomOut)) {
        console.log(`Attest SBOM ${target}`);
        const attestArgs = [
          "attest",
          ...cosignBaseArgs(),
          "--type",
          "spdx",
          "--predicate",
          sbomOut,
          target,
        ];
        const attestResult = run(cosign, attestArgs, { dryRun });
        if (attestResult.status !== 0) process.exit(attestResult.status ?? 1);
      }
    }

    signed.push(image);
  }

  writeManifest(images, dir, { channel: "build", phase: "attest" });
  console.log(`\nAttest complete for ${signed.length} image(s). Artifacts: ${path.relative(root, dir)}`);
}

function verify(images, flags) {
  requireRegistry();
  const cosign = toolPath("cosign");
  if (!flags.has("skip-cosign")) {
    if (!cosign) {
      console.error("cosign not found (use --skip-cosign for manifest-only checks).");
      process.exit(1);
    }
    const identity = defaultCertificateIdentity();
    const issuer = defaultOidcIssuer();
    const key = process.env.COSIGN_KEY?.trim();
    const keyless = !key && !process.env.COSIGN_PUBLIC_KEY?.trim();

    for (const image of images) {
      const target = image.ref;
      console.log(`\nVerify signature ${target}`);
      const args = ["verify"];
      if (keyless) {
        args.push("--certificate-identity-regexp", identity, "--certificate-oidc-issuer", issuer);
      } else if (process.env.COSIGN_PUBLIC_KEY?.trim()) {
        args.push("--key", process.env.COSIGN_PUBLIC_KEY.trim());
      } else {
        args.push("--key", key);
      }
      args.push(target);
      const result = run(cosign, args, { dryRun: flags.has("dry-run"), quiet: false });
      if (result.status !== 0) process.exit(result.status ?? 1);
    }
  } else {
    console.log("Skipping cosign verify (--skip-cosign).");
  }

  const tag = resolveTag();
  const dir = releaseDir(tag);
  if (!flags.has("skip-sbom")) {
    let found = 0;
    for (const image of images) {
      const file = sbomPath(dir, image.name);
      if (existsSync(file)) {
        found++;
        console.log(`ok: SBOM on disk ${path.relative(root, file)}`);
      }
    }
    if (found === 0) {
      console.warn("warn: no local SBOM files — run attest or download CI artifacts");
    }
  }

  console.log("\nVerify complete.");
}

function writeManifest(images, dir, meta = {}) {
  const tag = resolveTag();
  const manifest = {
    schema: "repody-release/v1",
    packageVersion: readPackageVersion(),
    releaseTag: tag,
    gitTag: gitTagAtHead(),
    gitSha: gitSha(),
    channel: meta.channel ?? "staging",
    phase: meta.phase ?? "manifest",
    createdAt: new Date().toISOString(),
    registry: resolveRegistry(),
    images: images.map((image) => ({
      role: image.role,
      name: image.name,
      tag: image.tag,
      ref: image.ref,
      digest: image.digest ?? null,
      refAtDigest: image.refAtDigest ?? null,
      sbom: existsSync(sbomPath(dir, image.name))
        ? path.relative(root, sbomPath(dir, image.name))
        : null,
    })),
  };
  const manifestPath = path.join(dir, "release-manifest.json");
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

  const helmPath = path.join(dir, "helm-images.yaml");
  writeFileSync(helmPath, helmImagesYaml(images), "utf8");

  const checksums = manifest.images
    .filter((i) => i.sbom)
    .map((i) => {
      const abs = path.join(root, i.sbom);
      return `${sha256File(abs)}  ${i.sbom}`;
    });
  if (checksums.length) {
    writeFileSync(path.join(dir, "SHA256SUMS"), `${checksums.join("\n")}\n`, "utf8");
  }

  console.log(`\nWrote ${path.relative(root, manifestPath)}`);
  console.log(`Wrote ${path.relative(root, helmPath)}`);
  return manifest;
}

function manifest(images, flags, channel) {
  const dir = releaseDir(resolveTag());
  writeManifest(images, dir, { channel, phase: "manifest" });
}

function promote(images, flags, channel) {
  console.log(`\n=== Release promotion (${channel}) ===\n`);
  verify(images, flags);
  const dir = releaseDir(resolveTag());
  const releaseManifest = writeManifest(images, dir, { channel, phase: "promote" });

  console.log("\n> Helm + client contract (deploy:check subset)\n");
  const checks = [
    ["helm-lint", "helm", ["lint", "deploy/helm/repody"]],
    [
      "helm-template-client-external",
      "helm",
      [
        "template",
        "repody",
        "deploy/helm/repody",
        "-f",
        "deploy/helm/repody/values.yaml",
        "-f",
        "deploy/helm/repody/values-common.yaml",
        "-f",
        "deploy/client/values-external.example.yaml",
        "-f",
        "deploy/client/values-enterprise.example.yaml",
      ],
    ],
    ["client-manifests", "node", ["deploy/scripts/check-client-manifests.mjs"]],
  ];
  for (const [label, cmd, args] of checks) {
    console.log(`> ${label}`);
    const result = run(cmd, args, { quiet: true });
    if (result.status !== 0) {
      console.error(`failed: ${label}`);
      process.exit(result.status ?? 1);
    }
    console.log(`ok: ${label}`);
  }

  console.log(`
Promotion gate passed for ${releaseManifest.releaseTag} (${channel}).

Handoff bundle:
  ${path.relative(root, path.join(dir, "release-manifest.json"))}
  ${path.relative(root, path.join(dir, "helm-images.yaml"))}

Client next steps:
  1. Merge helm-images.yaml image digests into GitOps values
  2. pnpm client:check -- --live (on staging cluster)
  3. Argo CD sync repody-data -> repody-auth -> repody
`);
}

function runCheckMode() {
  const registry = "example.invalid/repody";
  const env = {
    ...process.env,
    REPODY_IMAGE_REGISTRY: registry,
    REPODY_IMAGE_TAG: "0.0.0-check",
  };
  const cases = [
    ["unknown command", ["wat"], 1],
    ["manifest dry-run", ["manifest", "--dry-run", "--skip-digest"], 0],
    ["promote dry-run", ["promote", "--dry-run", "--skip-cosign", "--skip-sbom", "--skip-digest"], 0],
  ];
  for (const [name, args, expected] of cases) {
    const result = spawnSync(process.execPath, ["deploy/scripts/release-supply-chain.mjs", ...args], {
      cwd: root,
      env,
      encoding: "utf8",
    });
    if (result.status !== expected) {
      console.error(`check failed: ${name} expected exit ${expected}, got ${result.status}\n${result.stderr}`);
      process.exit(1);
    }
  }
  console.log("ok: release-supply-chain --check");
}

const { cmd, flags, channel } = parseArgs(process.argv);

if (flags.has("check")) {
  runCheckMode();
  process.exit(0);
}

if (!["attest", "verify", "manifest", "promote"].includes(cmd)) {
  console.error("Usage: release-supply-chain.mjs attest|verify|manifest|promote [--check]");
  process.exit(1);
}

let images = releaseImageSet();
try {
  images = await enrichWithDigests(images, flags);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

if (cmd === "attest") attest(images, flags);
else if (cmd === "verify") verify(images, flags);
else if (cmd === "manifest") manifest(images, flags, channel);
else if (cmd === "promote") promote(images, flags, channel);
