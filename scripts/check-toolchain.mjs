#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const expectedBun = packageJson.packageManager?.match(/^bun@(.+)$/)?.[1];
const expectedNodeMajor = packageJson.engines?.node?.match(/>=\s*(\d+)/)?.[1];
const failures = [];

if (expectedNodeMajor && process.versions.node.split(".")[0] !== expectedNodeMajor) {
  failures.push(
    `Node ${process.versions.node} does not match required major ${expectedNodeMajor}.x`,
  );
}

if (!expectedBun) {
  failures.push('package.json must pin "packageManager": "bun@<version>".');
} else {
  // Bun says which version started this (`bun run doctor`, `bun run platform`): no lookup on PATH.
  const actualBun = process.env.npm_config_user_agent?.match(/\bbun\/([^\s]+)/)?.[1];
  if (!actualBun) {
    failures.push(
      `Run this through Bun (bun run doctor). Bun ${expectedBun}: npm install --global bun@${expectedBun}`,
    );
  } else if (actualBun !== expectedBun) {
    failures.push(
      `Bun ${actualBun} does not match pinned ${expectedBun}. Run: npm install --global bun@${expectedBun}`,
    );
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`ok: Node ${process.versions.node}, Bun ${expectedBun}`);
