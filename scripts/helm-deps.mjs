#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const chartDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../deploy/helm/audit-platform"
);

const result = spawnSync("helm", ["dependency", "update", chartDir], {
  stdio: "inherit",
  shell: process.platform === "win32",
});

process.exit(result.status ?? 1);
