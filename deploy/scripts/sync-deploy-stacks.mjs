#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { STACKS } from "../platform-modules.mjs";

const outDir = join(process.cwd(), "deploy", "stacks");
const checkOnly = process.argv.includes("--check");

mkdirSync(outDir, { recursive: true });

let drift = false;

for (const stack of Object.values(STACKS)) {
  if (!stack.files.length) continue;
  const body = `${stack.files.join("\n")}\n`;
  const path = join(outDir, `${stack.id}.files`);
  if (checkOnly) {
    const existing = existsSync(path) ? readFileSync(path, "utf8") : "";
    if (existing !== body) {
      console.error(`Drift: ${path} (run pnpm deploy:sync-stacks)`);
      drift = true;
    }
    continue;
  }
  writeFileSync(path, body);
  console.error(`wrote ${path}`);
}

if (checkOnly && drift) {
  process.exit(1);
}
