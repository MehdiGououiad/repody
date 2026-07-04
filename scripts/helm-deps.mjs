#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const checkOnly = process.argv.includes("--check");
const ensure = process.argv.includes("--ensure");
const update = process.argv.includes("--update");
const charts = [
  "deploy/helm/repody-data",
  "deploy/helm/repody-auth",
  "deploy/helm/repody",
];

function lockedDependencies(chartDir) {
  const lockPath = path.join(chartDir, "Chart.lock");
  if (!existsSync(lockPath)) return [];
  const lock = readFileSync(lockPath, "utf8");
  const dependencies = [];
  let current = null;
  for (const line of lock.split(/\r?\n/)) {
    const name = line.match(/^\s*-\s+name:\s+(.+)\s*$/);
    if (name) {
      current = { name: name[1].trim() };
      dependencies.push(current);
      continue;
    }
    const version = line.match(/^\s+version:\s+(.+)\s*$/);
    if (version && current) {
      current.version = version[1].trim();
    }
  }
  return dependencies.filter((dependency) => dependency.name && dependency.version);
}

let failed = false;
for (const chart of charts) {
  const chartDir = path.join(root, chart);
  const missing = lockedDependencies(chartDir).filter(
    ({ name, version }) => !existsSync(path.join(chartDir, "charts", `${name}-${version}.tgz`)),
  );
  if (checkOnly || ensure) {
    if (!missing.length) {
      console.error(`ok: ${chart} chart dependencies present`);
      continue;
    }
    const missingMessage = `${chart} missing chart archives: ${missing
      .map(({ name, version }) => `${name}-${version}.tgz`)
      .join(", ")}`;
    console.error(missingMessage);
    if (checkOnly) {
      failed = true;
      continue;
    }
  }

  const command = update ? "update" : "build";
  const args = ["dependency", command];
  if (!update) args.push("--skip-refresh");
  args.push(chartDir);
  console.error(`> helm ${args.join(" ")}`);
  const result = spawnSync("helm", args, {
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) {
    failed = true;
  }
}

process.exit(failed ? 1 : 0);
