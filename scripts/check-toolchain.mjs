#!/usr/bin/env node
import { spawnSync } from "node:child_process";
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
  // `bun run doctor` runs this under Node and says which Bun started it; plain `node` asks bun.
  let actualBun = process.env.npm_config_user_agent?.match(/\bbun\/([^\s]+)/)?.[1];
  if (!actualBun) {
    // Through a shell: on Windows an npm-installed bun is a bun.cmd shim, which only a shell
    // runs. One constant command string, so nothing is passed as arguments to a shell.
    const result = spawnSync("bun --version", { cwd: root, encoding: "utf8", shell: true });
    actualBun = result.stdout?.trim();
  }
  if (!actualBun) {
    failures.push(`Bun ${expectedBun} is required. Run: npm install --global bun@${expectedBun}`);
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
