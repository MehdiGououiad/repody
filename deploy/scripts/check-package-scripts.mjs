#!/usr/bin/env node
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const packageJson = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const scripts = new Set(Object.keys(packageJson.scripts ?? {}));
const packageDependencies = {
  ...packageJson.dependencies,
  ...packageJson.devDependencies,
  ...packageJson.optionalDependencies,
};
const pnpmBuiltins = new Set(["dlx", "exec", "install", "update"]);
const packageManagedBins = new Map([
  ["eslint", "eslint"],
  ["next", "next"],
  ["openapi-typescript", "openapi-typescript"],
  ["playwright", "@playwright/test"],
  ["tsc", "typescript"],
]);
const failures = [];
const generatedPaths = new Set([".next/standalone/server.js"]);

function tokenize(segment) {
  return [...segment.matchAll(/"([^"]*)"|'([^']*)'|(\S+)/g)].map(
    (match) => match[1] ?? match[2] ?? match[3],
  );
}

function isOptionValue(token) {
  return token.startsWith("-") || token.includes("://") || token.includes("*");
}

function looksLocal(token) {
  if (!token || isOptionValue(token) || /^[A-Z_]+=/.test(token)) return false;
  if (/^[\w.-]+:[\w.-]+$/.test(token)) return false;
  return (
    token.includes("/") ||
    token.includes("\\") ||
    /\.(mjs|js|ts|tsx|py|json|yaml|yml|md|pdf)$/.test(token) ||
    ["app", "components", "lib", "proxy.ts"].includes(token)
  );
}

function checkPath(scriptName, cwd, token) {
  if (generatedPaths.has(token.replaceAll("\\", "/"))) return;
  const abs = resolve(cwd, token);
  if (!existsSync(abs)) {
    failures.push(`${scriptName}: missing local path "${token}"`);
  }
}

function checkNodeEntrypoint(scriptName, cwd, tokens) {
  const entry = tokens.slice(1).find((token) => !token.startsWith("-"));
  if (entry && /\.(mjs|js)$/.test(entry)) {
    checkPath(scriptName, cwd, entry);
  }
}

function checkBackendRunner(scriptName, tokens) {
  const entryIndex = tokens.indexOf("scripts/backend-run.mjs");
  if (entryIndex === -1) return false;
  const backendCwd = resolve(root, "backend");
  for (const token of tokens.slice(entryIndex + 1)) {
    if (looksLocal(token)) {
      checkPath(scriptName, backendCwd, token);
    }
  }
  if (tokens.includes("pytest") && !tokens.includes("--dev")) {
    failures.push(`${scriptName}: backend pytest commands must pass --dev to scripts/backend-run.mjs`);
  }
  return true;
}

function checkPythonEntrypoint(scriptName, cwd, tokens) {
  if (tokens.includes("-m")) return;
  const entry = tokens.slice(1).find((token) => !token.startsWith("-"));
  if (entry && entry.endsWith(".py")) {
    checkPath(scriptName, cwd, entry);
  }
}

function checkSegment(scriptName, cwd, segment) {
  const tokens = tokenize(segment);
  if (!tokens.length) return cwd;

  if (tokens[0] === "cd") {
    const nextCwd = resolve(cwd, tokens[1] ?? ".");
    if (!existsSync(nextCwd) || !statSync(nextCwd).isDirectory()) {
      failures.push(`${scriptName}: missing working directory "${tokens[1] ?? ""}"`);
    }
    return nextCwd;
  }

  if (tokens[0] === "node") {
    checkNodeEntrypoint(scriptName, cwd, tokens);
    if (checkBackendRunner(scriptName, tokens)) return cwd;
  }

  if (tokens[0] === "python") {
    checkPythonEntrypoint(scriptName, cwd, tokens);
  }

  if (tokens[0] === "uv" && tokens[1] === "run") {
    const pythonIndex = tokens.indexOf("python");
    if (pythonIndex >= 0) {
      checkPythonEntrypoint(scriptName, cwd, tokens.slice(pythonIndex));
    }
  }

  if (tokens[0] === "playwright" && tokens[1] === "test") {
    for (const token of tokens.slice(2)) {
      if (/\.(ts|js)$/.test(token)) {
        checkPath(scriptName, cwd, token);
      }
    }
  }

  if (tokens[0] === "pnpm") {
    checkPnpmScriptReference(scriptName, tokens);
  } else {
    checkPackageManagedBinary(scriptName, tokens[0]);
  }

  for (const token of tokens.slice(1)) {
    if (looksLocal(token)) {
      checkPath(scriptName, cwd, token);
    }
  }

  return cwd;
}

function checkPackageManagedBinary(scriptName, command) {
  const packageName = packageManagedBins.get(command);
  if (packageName && !packageDependencies[packageName]) {
    failures.push(`${scriptName}: "${command}" requires package dependency "${packageName}"`);
  }
}

function checkPnpmScriptReference(scriptName, tokens) {
  const command = tokens.slice(1).find((token) => !token.startsWith("-"));
  if (!command) return;
  if (command === "exec") {
    const binary = tokens.slice(tokens.indexOf("exec") + 1).find((token) => !token.startsWith("-"));
    if (binary) {
      checkPackageManagedBinary(scriptName, binary);
    }
  }
  if (pnpmBuiltins.has(command)) return;
  if (!scripts.has(command)) {
    failures.push(`${scriptName}: references missing pnpm script "${command}"`);
  }
}

function checkBackendToolchain(scriptName, command) {
  if (!/\bcd\s+backend\b/.test(command)) return;
  if (/\buv\s+run\b/.test(command)) {
    failures.push(`${scriptName}: use "node scripts/backend-run.mjs" instead of repeating "cd backend && uv run"`);
  }
  if (/\bcd\s+backend\s*&&\s*(python|pytest|alembic|uvicorn)\b/.test(command)) {
    failures.push(`${scriptName}: backend commands must use "node scripts/backend-run.mjs"`);
  }
  if (/\bpytest\b/.test(command) && !/\buv\s+run\s+--extra\s+dev\s+pytest\b/.test(command)) {
    failures.push(`${scriptName}: backend pytest commands must use "node scripts/backend-run.mjs --dev pytest"`);
  }
  if (
    /\bscripts\/platform_integration_suite\.py\b/.test(command) &&
    !/\buv\s+run\s+--extra\s+dev\s+python\b/.test(command)
  ) {
    failures.push(`${scriptName}: backend integration test commands must use "node scripts/backend-run.mjs --dev python"`);
  }
}

for (const [scriptName, command] of Object.entries(packageJson.scripts ?? {})) {
  checkBackendToolchain(scriptName, command);
  let cwd = root;
  for (const segment of command.split("&&").map((part) => part.trim())) {
    cwd = checkSegment(scriptName, cwd, segment);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("ok: package scripts reference existing local paths, pnpm aliases, package tools, and backend toolchain");
