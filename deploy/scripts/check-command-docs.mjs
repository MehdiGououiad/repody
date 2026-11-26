#!/usr/bin/env node
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const scripts = new Set(Object.keys(packageJson.scripts ?? {}));
// Bun's own commands (`bun --help`). `bun <name>` runs one of these when it exists, so a package
// script with the same name needs `bun run <name>` (`bun build` is Bun's bundler, not the build
// script). `bun check` and `bun fmt` run the project's script of that name (`bun check --help`).
const bunCommands = new Set([
  "run",
  "test",
  "check",
  "fmt",
  "x",
  "repl",
  "exec",
  "install",
  "add",
  "remove",
  "update",
  "audit",
  "outdated",
  "link",
  "unlink",
  "publish",
  "patch",
  "pm",
  "info",
  "why",
  "build",
  "init",
  "create",
  "upgrade",
  "dedupe",
  "prune",
]);
// Docs, and the scripts and config files whose comments and messages name commands too.
const rootDocs = new Set([
  "CONTEXT.md",
  "README.md",
  "compose.yaml",
  "compose.portable.yaml",
  "docker-bake.hcl",
  "Dockerfile.web",
]);
const docRoots = ["deploy", "docs", "e2e", "scripts"];
const checkedExtensions = [".md", ".mjs", ".yaml", ".yml", ".sh"];
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
// Single spaces, as the docs write commands: no backtracking between optional groups.
const commandPattern = /\bbun (run )?([A-Za-z][\w:-]*)/g;
const forbiddenText = [
  { pattern: /�/, label: "Unicode replacement character" },
  { pattern: /[ÂÃ]/, label: "mojibake marker" },
  { pattern: /â(?:€|†|„|…|œ|�)/, label: "mojibake marker" },
];

function discoverFiles() {
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
    if (entry.isFile() && checkedExtensions.some((ext) => entry.name.endsWith(ext))) {
      docs.push(abs);
    }
  }
}

const self = fileURLToPath(import.meta.url);

for (const abs of discoverFiles().filter((file) => resolve(file) !== resolve(self))) {
  const text = readFileSync(abs, "utf8");
  for (const { pattern, label } of forbiddenText) {
    const match = pattern.exec(text);
    if (match?.index !== undefined) {
      const line = text.slice(0, match.index).split(/\r?\n/).length;
      missing.push(`${relative(root, abs)}:${line} contains ${label}`);
    }
  }
  for (const match of text.matchAll(commandPattern)) {
    const [, viaRun, command] = match;
    const line = text.slice(0, match.index).split(/\r?\n/).length;
    const where = `${relative(root, abs)}:${line}`;
    if (viaRun) {
      if (!scripts.has(command))
        missing.push(`${where} references missing package script "${command}"`);
    } else if (!bunCommands.has(command) && !scripts.has(command)) {
      missing.push(`${where} references missing package script "${command}"`);
    } else if (command === "build") {
      missing.push(
        `${where}: \`bun build\` is Bun's bundler; the build script is \`bun run build\``,
      );
    }
  }
}

if (missing.length) {
  console.error(missing.join("\n"));
  process.exit(1);
}

console.log(
  "ok: bun commands named in docs, scripts and config, and doc hygiene (links: lychee in CI)",
);
