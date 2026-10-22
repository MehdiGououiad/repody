#!/usr/bin/env node
/**
 * Local security scan: dependency audits, Trivy (fs/config/secret/images), Grype on Syft SBOMs.
 *
 *   pnpm security:scan         full scan (builds images when Docker is available)
 *   pnpm security:scan:quick   deps + Trivy fs/config/secret only
 *   pnpm security:scan:check   wiring validation for deploy:check
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildSecurityReport } from "./security-report.mjs";

export const TRIVY_VERSION = "0.74.0";
export const GRYPE_IMAGE = "anchore/grype:v0.119.0";
export const SYFT_IMAGE = "anchore/syft:v1.52.0";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = resolve(root, "dist/security");
const checkOnly = process.argv.includes("--check");
const skipImages =
  process.argv.includes("--quick") || process.env.REPODY_SECURITY_SKIP_IMAGES === "1";

/** Scan these paths only - avoids .next/node_modules churn on local dev. */
const FS_TARGETS = ["backend", "pnpm-lock.yaml", "deploy"];

function run(cmd, args, opts = {}) {
  // pnpm is a .cmd shim. Node cannot spawn it directly (ENOENT / EINVAL).
  const windowsCmd = process.platform === "win32" && cmd === "pnpm";
  const spawnCmd = windowsCmd ? process.env.ComSpec || "cmd.exe" : cmd;
  const spawnArgs = windowsCmd ? ["/d", "/s", "/c", "pnpm.cmd", ...args] : args;
  const result = spawnSync(spawnCmd, spawnArgs, {
    cwd: opts.cwd ?? root,
    encoding: "utf8",
    env: { ...process.env, ...opts.env },
    shell: false,
    stdio: opts.capture ? ["ignore", "pipe", "pipe"] : "inherit",
  });
  if (opts.capture) {
    return result;
  }
  if (result.status !== 0 && !opts.allowFail) {
    process.exit(result.status ?? 1);
  }
  return result;
}

function writeAuditJson(path, stdout, label, shape) {
  const raw = stdout?.trim() ?? "";
  if (!raw) {
    throw new Error(`${label} produced no JSON`);
  }
  const doc = JSON.parse(raw);
  const ok =
    shape === "array"
      ? Array.isArray(doc)
      : doc != null && typeof doc === "object" && !Array.isArray(doc);
  if (!ok) {
    throw new Error(`${label} JSON has the wrong shape`);
  }
  writeFileSync(path, `${raw}\n`, "utf8");
}

function dockerMountSrc() {
  return process.platform === "win32" ? `${root.replace(/\\/g, "/")}:/src` : `${root}:/src`;
}

function dockerMountOut() {
  const out = process.platform === "win32" ? outDir.replace(/\\/g, "/") : outDir;
  return `${out}:/out`;
}

function dockerTrivy(args, allowFail = false) {
  return run(
    "docker",
    [
      "run",
      "--rm",
      "-v",
      dockerMountSrc(),
      "-v",
      "repody-trivy-cache:/root/.cache/trivy",
      ...(args[0] === "image" ? ["-v", "/var/run/docker.sock:/var/run/docker.sock"] : []),
      "-w",
      "/src",
      `aquasec/trivy:${TRIVY_VERSION}`,
      ...args,
    ],
    { allowFail }
  );
}

function hasDocker() {
  const r = spawnSync("docker", ["info"], { encoding: "utf8", stdio: "ignore" });
  return r.status === 0;
}

function hasTrivyLocal() {
  const r = spawnSync("trivy", ["--version"], { encoding: "utf8", stdio: "ignore" });
  return r.status === 0;
}

function trivyFsOutput(label) {
  const safe = label.replace(/[^a-z0-9_-]+/gi, "_");
  return `dist/security/trivy-fs-${safe}.json`;
}

function trivySecretOutput(label) {
  const safe = label.replace(/[^a-z0-9_-]+/gi, "_");
  return `dist/security/trivy-secret-${safe}.json`;
}

function trivy(args, allowFail = false) {
  if (hasTrivyLocal()) {
    return run("trivy", args, { allowFail });
  }
  if (!hasDocker()) {
    console.error("Install trivy or Docker to run filesystem scans.");
    process.exit(1);
  }
  return dockerTrivy(args, allowFail);
}

async function main() {
  if (checkOnly) {
    const required = [
      "deploy/scripts/security-scan.mjs",
      "deploy/scripts/security-report.mjs",
      "deploy/security/trivy.yaml",
      "deploy/security/trivy-secret.yaml",
      ".github/workflows/security.yml",
    ];
    for (const rel of required) {
      if (!existsSync(resolve(root, rel))) {
        console.error(`security:scan --check: missing ${rel}`);
        process.exit(1);
      }
    }
    console.log("security:scan wiring OK");
    return;
  }

  mkdirSync(outDir, { recursive: true });
  for (const name of readdirSync(outDir)) {
    if (/^(trivy-|grype-|syft-|pnpm-audit|pip-audit)/.test(name)) {
      unlinkSync(resolve(outDir, name));
    }
  }
  console.log(`Security scan → ${outDir}`);
  console.log(`Trivy ${TRIVY_VERSION} · ${GRYPE_IMAGE} · ${SYFT_IMAGE}`);

  const totalSteps = 6;
  let step = 0;

  console.log(`\n[${++step}/${totalSteps}] pnpm audit`);
  const pnpm = run("pnpm", ["audit", "--json"], { capture: true, allowFail: true });
  writeAuditJson(resolve(outDir, "pnpm-audit.json"), pnpm.stdout, "pnpm audit", "object");

  console.log(`\n[${++step}/${totalSteps}] pip-audit`);
  // pip-audit 2.10 does not read uv.lock. Export the lock, then audit that file.
  const requirementsPath = resolve(outDir, "backend-requirements.txt");
  const exported = run(
    "uv",
    [
      "export",
      "--frozen",
      "--directory",
      "backend",
      "--no-emit-project",
      "--format",
      "requirements-txt",
      "-o",
      requirementsPath,
    ],
    { capture: true, allowFail: true }
  );
  if (exported.status !== 0) {
    console.error(exported.stderr || exported.stdout || "uv export failed");
    process.exit(exported.status ?? 1);
  }
  const pip = run(
    "uvx",
    ["pip-audit", "-r", requirementsPath, "-f", "json", "--progress-spinner", "off"],
    { capture: true, allowFail: true }
  );
  writeAuditJson(resolve(outDir, "pip-audit.json"), pip.stdout, "pip-audit", "object");

  console.log(`\n[${++step}/${totalSteps}] Trivy filesystem`);
  for (const target of FS_TARGETS) {
    console.log(`  → ${target}`);
    trivy(
      [
        "fs",
        "--config",
        "deploy/security/trivy.yaml",
        "--scanners",
        "vuln,license",
        "--format",
        "json",
        "--output",
        trivyFsOutput(target),
        target,
      ],
      true
    );
  }

  console.log(`\n[${++step}/${totalSteps}] Trivy config (Dockerfile, Compose)`);
  for (const target of ["backend/Dockerfile", "Dockerfile.web", "compose.yaml"]) {
    console.log(`  → ${target}`);
    trivy(
      [
        "config",
        "--config",
        "deploy/security/trivy.yaml",
        "--format",
        "json",
        "--output",
        `dist/security/trivy-config-${target.replace(/[^a-z0-9._-]+/gi, "_")}.json`,
        target,
      ],
      true
    );
  }

  console.log(`\n[${++step}/${totalSteps}] Trivy secret scan`);
  for (const target of FS_TARGETS) {
    console.log(`  → ${target}`);
    trivy(
      [
        "fs",
        "--config",
        "deploy/security/trivy.yaml",
        "--scanners",
        "secret",
        "--format",
        "json",
        "--output",
        trivySecretOutput(target),
        target,
      ],
      true
    );
  }

  if (!skipImages) {
    if (!hasDocker()) {
      console.warn(
        `\n[${++step}/${totalSteps}] Skipping image scan (Docker unavailable). Use --quick to silence.`
      );
    } else {
      console.log(`\n[${++step}/${totalSteps}] Build + Trivy image + Syft + Grype`);
      run("node", ["deploy/scripts/build-images.mjs"], {
        env: {
          REPODY_BACKEND_IMAGE_TAG: "security-scan",
          REPODY_WEB_IMAGE_TAG: "security-scan",
        },
      });

      const backendImg = "repody-backend:security-scan";
      const webImg = "repody-web:security-scan";

      trivy(
        [
          "image",
          "--config",
          "deploy/security/trivy.yaml",
          "--format",
          "json",
          "--output",
          "dist/security/trivy-image-backend.json",
          backendImg,
        ],
        true
      );
      trivy(
        [
          "image",
          "--config",
          "deploy/security/trivy.yaml",
          "--format",
          "json",
          "--output",
          "dist/security/trivy-image-web.json",
          webImg,
        ],
        true
      );

      run(
        "docker",
        [
          "run",
          "--rm",
          "-v",
          "/var/run/docker.sock:/var/run/docker.sock",
          "-v",
          dockerMountOut(),
          SYFT_IMAGE,
          backendImg,
          "-o",
          "spdx-json=/out/syft-backend.spdx.json",
        ],
        { allowFail: true }
      );
      run(
        "docker",
        [
          "run",
          "--rm",
          "-v",
          dockerMountOut(),
          GRYPE_IMAGE,
          "sbom:/out/syft-backend.spdx.json",
          "-o",
          "json",
          "--file",
          "/out/grype-backend.json",
        ],
        { allowFail: true }
      );
      run(
        "docker",
        [
          "run",
          "--rm",
          "-v",
          "/var/run/docker.sock:/var/run/docker.sock",
          "-v",
          dockerMountOut(),
          SYFT_IMAGE,
          webImg,
          "-o",
          "spdx-json=/out/syft-web.spdx.json",
        ],
        { allowFail: true }
      );
      run(
        "docker",
        [
          "run",
          "--rm",
          "-v",
          dockerMountOut(),
          GRYPE_IMAGE,
          "sbom:/out/syft-web.spdx.json",
          "-o",
          "json",
          "--file",
          "/out/grype-web.json",
        ],
        { allowFail: true }
      );
    }
  } else {
    console.log(`\n[${++step}/${totalSteps}] Skipped (--quick / REPODY_SECURITY_SKIP_IMAGES)`);
  }

  const { status, gatedTotal, reportPath } = buildSecurityReport();
  console.log(`\n${status}: ${gatedTotal} CRITICAL/HIGH findings`);
  console.log(`Report: ${reportPath}`);
  process.exit(status === "PASS" ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
