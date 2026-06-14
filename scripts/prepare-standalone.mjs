#!/usr/bin/env node
/**
 * Copy public/ and .next/static into .next/standalone for local production runs.
 * Mirrors Dockerfile.web runner stage (required for output: "standalone").
 */
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const standaloneDir = join(root, ".next", "standalone");
const serverPath = join(standaloneDir, "server.js");

if (!existsSync(serverPath)) {
  console.error("Missing .next/standalone/server.js — run `pnpm build` first.");
  process.exit(1);
}

function copyDir(src, dest) {
  if (!existsSync(src)) return;
  mkdirSync(dest, { recursive: true });
  cpSync(src, dest, { recursive: true, force: true });
}

copyDir(join(root, "public"), join(standaloneDir, "public"));
copyDir(join(root, ".next", "static"), join(standaloneDir, ".next", "static"));

console.error("✓ Standalone server prepared (public + static copied)");
