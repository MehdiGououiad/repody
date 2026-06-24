#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const charts = [
  "deploy/helm/repody-data",
  "deploy/helm/repody-queue",
  "deploy/helm/repody",
];

let failed = false;
for (const chart of charts) {
  const chartDir = path.join(root, chart);
  console.error(`> helm dependency update ${chart}`);
  const result = spawnSync("helm", ["dependency", "update", chartDir], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    failed = true;
  }
}

process.exit(failed ? 1 : 0);
