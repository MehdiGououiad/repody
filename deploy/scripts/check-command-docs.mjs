#!/usr/bin/env node
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const scripts = new Set(Object.keys(packageJson.scripts ?? {}));
const pnpmBuiltins = new Set(["dlx", "exec", "install", "update"]);
const rootDocs = new Set(["CONTEXT.md", "README.md"]);
const docRoots = ["deploy", "docs", "e2e"];
const skipDirs = new Set([
  ".git",
  ".next",
  ".venv",
  "charts",
  "node_modules",
  "src",
  "test-results",
]);

const missing = [];
const commandPattern = /\bpnpm\s+([A-Za-z][A-Za-z0-9:_-]*)/g;
const forbiddenText = [
  { pattern: /�/, label: "Unicode replacement character" },
  { pattern: /[ÂÃ]/, label: "mojibake marker" },
  { pattern: /â(?:€|†|„|…|œ|�)/, label: "mojibake marker" },
];

function discoverMarkdownDocs() {
  const docs = [];
  for (const name of rootDocs) {
    const abs = resolve(root, name);
    try {
      if (statSync(abs).isFile()) {
        docs.push(abs);
      }
    } catch {
      // Optional contributor guide may not exist in downstream forks.
    }
  }
  for (const dir of docRoots) {
    walk(resolve(root, dir), docs);
  }
  return docs.sort((a, b) => relative(root, a).localeCompare(relative(root, b)));
}

function walk(dir, docs) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    const abs = resolve(dir, entry.name);
    if (entry.isDirectory()) {
      if (!skipDirs.has(entry.name)) {
        walk(abs, docs);
      }
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".md")) {
      docs.push(abs);
    }
  }
}

for (const abs of discoverMarkdownDocs()) {
  const text = readFileSync(abs, "utf8");
  for (const { pattern, label } of forbiddenText) {
    const match = pattern.exec(text);
    if (match?.index !== undefined) {
      const line = text.slice(0, match.index).split(/\r?\n/).length;
      missing.push(`${relative(root, abs)}:${line} contains ${label}`);
    }
  }
  for (const match of text.matchAll(commandPattern)) {
    const command = match[1];
    if (scripts.has(command) || pnpmBuiltins.has(command)) {
      continue;
    }
    const line = text.slice(0, match.index).split(/\r?\n/).length;
    missing.push(`${relative(root, abs)}:${line} references missing pnpm script "${command}"`);
  }
}

if (missing.length) {
  console.error(missing.join("\n"));
  process.exit(1);
}

console.log("ok: documented pnpm commands and doc hygiene (links: lychee in CI)");
