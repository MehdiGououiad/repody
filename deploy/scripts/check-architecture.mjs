#!/usr/bin/env node
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const failures = [];

const PY_IMPORT_RE = /^\s*(?:from|import)\s+([A-Za-z0-9_.]+)/gm;

/** @typedef {{ name: string, dir?: string, files?: string[], forbiddenImports: RegExp[], forbiddenText?: RegExp[] }} ArchRule */

/** @type {ArchRule[]} */
const architectureRules = [
  {
    name: "Platform contracts",
    dir: "backend/src/repody/platform/contracts",
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^repody\.(api|db|settings|storage|taskiq|extraction|rules|services)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
  },
  {
    name: "Platform recipe (no services lifecycle)",
    files: ["backend/src/repody/platform/recipe.py"],
    forbiddenImports: [/^repody\.services(?:\.|$)/],
  },
  {
    name: "Platform agent_metadata (no services)",
    files: ["backend/src/repody/platform/agent_metadata.py"],
    forbiddenImports: [/^repody\.services(?:\.|$)/],
  },
  {
    name: "Platform metrics build",
    dir: "backend/src/repody/platform/metrics",
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^repody\.(api|db|storage|taskiq)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
  },
  {
    name: "Platform run pure+contracts",
    dir: "backend/src/repody/platform/run",
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^repody\.(api|db|settings|storage|taskiq|services)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
  },
  {
    name: "Platform operator",
    dir: "backend/src/repody/platform/operator",
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^repody\.(api|db|storage|taskiq|services)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
  },
  {
    name: "IDP contracts (flat)",
    files: ["backend/src/repody/agents/idp/contracts.py"],
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^repody\.(api|db|settings|storage|taskiq|services)(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
  },
  {
    name: "IDP compose (flat, port-injected)",
    files: ["backend/src/repody/agents/idp/compose.py"],
    forbiddenImports: [
      /^sqlalchemy(?:\.|$)/,
      /^fastapi(?:\.|$)/,
      /^redis(?:\.|$)/,
      /^structlog(?:\.|$)/,
      /^repody\.(api|db|settings|storage|taskiq|services)(?:\.|$)/,
      /^repody\.agents\.idp\.adapters(?:\.|$)/,
    ],
    forbiddenText: [/\bAsyncSession\b/, /\bsession\s*:/],
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

function resolveRuleFiles(rule) {
  if (rule.files?.length) {
    return rule.files.map((rel) => resolve(root, rel));
  }
  if (!rule.dir) {
    return [];
  }
  const absDir = resolve(root, rule.dir);
  try {
    if (!statSync(absDir).isDirectory()) {
      failures.push(`${rule.name}: missing directory ${rule.dir}`);
      return [];
    }
  } catch {
    failures.push(`${rule.name}: missing directory ${rule.dir}`);
    return [];
  }
  return walkPython(rule.dir);
}

for (const rule of architectureRules) {
  for (const file of resolveRuleFiles(rule)) {
    let text;
    try {
      text = readFileSync(file, "utf8");
    } catch {
      failures.push(`${rule.name}: missing file ${relative(root, file)}`);
      continue;
    }
    const rel = relative(root, file);
    for (const match of text.matchAll(PY_IMPORT_RE)) {
      const imported = match[1];
      if (rule.forbiddenImports.some((pattern) => pattern.test(imported))) {
        failures.push(
          `${rel}:${lineNumber(text, match.index ?? 0)} ${rule.name} imports outer detail "${imported}"`,
        );
      }
    }
    for (const pattern of rule.forbiddenText ?? []) {
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
