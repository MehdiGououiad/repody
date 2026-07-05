#!/usr/bin/env node
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const failures = [];

const PY_IMPORT_RE = /^\s*(?:from|import)\s+([A-Za-z0-9_.]+)/gm;

const runInnerLayerRules = [
  {
    name: "Run domain",
    dir: "backend/src/audit_workbench/services/run/domain",
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^audit_workbench\.(api|db|settings|storage|taskiq)(?:\.|$)/,
      /^audit_workbench\.services\.run\.adapters(?:\.|$)/,
      /^audit_workbench\.services\.(run_events|run\.progress_persist|run\.progress_plan)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
  },
  {
    name: "Run application",
    dir: "backend/src/audit_workbench/services/run/application",
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^audit_workbench\.(api|db|settings|storage|taskiq)(?:\.|$)/,
      /^audit_workbench\.services\.run\.adapters(?:\.|$)/,
      /^audit_workbench\.services\.(run_events|run\.progress_persist|run\.progress_plan)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/, /type:\s*ignore/],
  },
];

function walkPython(dir) {
  const abs = resolve(root, dir);
  const files = [];
  for (const entry of readdirSync(abs, { withFileTypes: true })) {
    const path = resolve(abs, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkPython(relative(root, path)));
    } else if (entry.isFile() && entry.name.endsWith(".py")) {
      files.push(path);
    }
  }
  return files;
}

function lineNumber(text, index) {
  return text.slice(0, index).split(/\r?\n/).length;
}

for (const rule of runInnerLayerRules) {
  const absDir = resolve(root, rule.dir);
  try {
    if (!statSync(absDir).isDirectory()) {
      failures.push(`${rule.name}: missing directory ${rule.dir}`);
      continue;
    }
  } catch {
    failures.push(`${rule.name}: missing directory ${rule.dir}`);
    continue;
  }

  for (const file of walkPython(rule.dir)) {
    const rel = relative(root, file);
    const text = readFileSync(file, "utf8");
    for (const match of text.matchAll(PY_IMPORT_RE)) {
      const imported = match[1];
      if (rule.forbiddenImports.some((pattern) => pattern.test(imported))) {
        failures.push(
          `${rel}:${lineNumber(text, match.index ?? 0)} ${rule.name} imports outer detail "${imported}"`,
        );
      }
    }
    for (const pattern of rule.forbiddenText) {
      const match = pattern.exec(text);
      if (match?.index !== undefined) {
        failures.push(`${rel}:${lineNumber(text, match.index)} ${rule.name} contains ${pattern}`);
      }
    }
  }
}

const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
if (!packageJson.scripts?.["review:check"]?.includes("deploy:check")) {
  failures.push('package.json: review:check must include "pnpm deploy:check"');
}

const codeQuality = readFileSync(resolve(root, "docs/CODE-QUALITY.md"), "utf8");
if (!codeQuality.includes("pnpm review:check")) {
  failures.push("docs/CODE-QUALITY.md: must document pnpm review:check");
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("ok: architecture dependency rules");
