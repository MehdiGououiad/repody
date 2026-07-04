#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const expectedPnpm = packageJson.packageManager?.match(/^pnpm@(.+)$/)?.[1];
const expectedNodeMajor = packageJson.engines?.node?.match(/>=\s*(\d+)/)?.[1];
const failures = [];

if (expectedNodeMajor && process.versions.node.split(".")[0] !== expectedNodeMajor) {
  failures.push(
    `Node ${process.versions.node} does not match required major ${expectedNodeMajor}.x`,
  );
}

if (!expectedPnpm) {
  failures.push('package.json must pin "packageManager": "pnpm@<version>".');
} else {
  const userAgentPnpm = process.env.npm_config_user_agent?.match(/\bpnpm\/([^\s]+)/)?.[1];
  let actualPnpm = userAgentPnpm;

  if (!actualPnpm) {
    const result = spawnSync(process.platform === "win32" ? "pnpm.cmd" : "pnpm", ["--version"], {
      cwd: root,
      encoding: "utf8",
      shell: false,
    });
    actualPnpm = result.stdout?.trim();
  }

  if (!actualPnpm) {
    failures.push(`pnpm ${expectedPnpm} is required. Run: corepack enable`);
  } else if (actualPnpm !== expectedPnpm) {
    failures.push(
      `pnpm ${actualPnpm || "(unknown)"} does not match pinned ${expectedPnpm}. Run: corepack enable`,
    );
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`ok: Node ${process.versions.node}, pnpm ${expectedPnpm}`);
