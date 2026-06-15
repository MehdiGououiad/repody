#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const steps = [
  ["sync-stacks", "node", ["deploy/scripts/sync-deploy-stacks.mjs", "--check"]],
  ["validate-compose", "node", ["deploy/scripts/validate-compose-stacks.mjs"]],
  ["verify-helm-parity", "node", ["deploy/scripts/verify-helm-compose-parity.mjs"]],
];

if (process.platform !== "win32") {
  steps.push(["validate-vps", "bash", ["deploy/cloud/validate.sh"]]);
}

let failed = false;
for (const [label, cmd, args] of steps) {
  console.error(`\n▶ ${label}\n`);
  if (spawnSync(cmd, args, { stdio: "inherit" }).status !== 0) {
    failed = true;
    console.error(`\n✗ ${label} failed\n`);
  }
}

process.exit(failed ? 1 : 0);
