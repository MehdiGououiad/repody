/**
 * Content-aware local image tags — rebuild when source changes, not only on git commit.
 */
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";

const BACKEND_PATHS = [
  "backend/src",
  "backend/scripts",
  "backend/pyproject.toml",
  "backend/alembic",
  "backend/alembic.ini",
  "backend/Dockerfile",
  "backend/benchmark-fixtures",
];

const WEB_PATHS = [
  "app",
  "components",
  "lib",
  "public",
  "proxy.ts",
  "package.json",
  "pnpm-lock.yaml",
  "pnpm-workspace.yaml",
  ".npmrc",
  "next.config.ts",
  "next.config.mjs",
  "tsconfig.json",
  "postcss.config.mjs",
  "tailwind.config.ts",
  "Dockerfile.web",
];

const SKIP_DIR_NAMES = new Set([
  ".git",
  "node_modules",
  ".next",
  "__pycache__",
  ".pytest_cache",
  ".venv",
  "dist",
  "build",
]);

function gitShortSha(root) {
  try {
    const result = spawnSync("git", ["rev-parse", "--short=12", "HEAD"], {
      cwd: root,
      encoding: "utf8",
      shell: process.platform === "win32",
    });
    if (result.status === 0) {
      const sha = result.stdout.trim();
      if (sha) return sha;
    }
  } catch {
    // ignore
  }
  return "local";
}

function walkFiles(absPath, files = []) {
  let stat;
  try {
    stat = statSync(absPath);
  } catch {
    return files;
  }
  if (stat.isDirectory()) {
    const base = path.basename(absPath);
    if (SKIP_DIR_NAMES.has(base)) return files;
    for (const entry of readdirSync(absPath)) {
      walkFiles(path.join(absPath, entry), files);
    }
    return files;
  }
  if (stat.isFile()) {
    files.push(absPath);
  }
  return files;
}

function hashPaths(root, relPaths) {
  const hash = createHash("sha256");
  const files = [];
  for (const rel of relPaths) {
    const abs = path.join(root, rel);
    walkFiles(abs, files);
  }
  files.sort();
  for (const file of files) {
    hash.update(file.slice(root.length + 1));
    hash.update("\0");
    try {
      const data = readFileSync(file);
      hash.update(data);
    } catch {
      hash.update("missing");
    }
    hash.update("\0");
  }
  return hash.digest("hex").slice(0, 10);
}

/**
 * @param {string} root
 * @returns {{ backend: string, web: string, label: string }}
 */
export function resolveLocalImageTags(root) {
  const git = gitShortSha(root);
  const backendHash = hashPaths(root, BACKEND_PATHS);
  const webHash = hashPaths(root, WEB_PATHS);
  return {
    backend: `${git}-be-${backendHash}`,
    web: `${git}-fe-${webHash}`,
    label: `backend=${git}-be-${backendHash} web=${git}-fe-${webHash}`,
  };
}
