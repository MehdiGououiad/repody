#!/usr/bin/env node
/**
 * Modular platform CLI — compose stacks from deploy modules.
 *
 * Usage:
 *   node scripts/platform.mjs modules
 *   node scripts/platform.mjs stacks
 *   node scripts/platform.mjs up --stack=dev-warm --with=obs,errors
 *   node scripts/platform.mjs up --stack=prod-scale --with=obs,errors --scale-worker=3
 *   node scripts/platform.mjs down --stack=dev-warm --with=obs,errors
 *   node scripts/platform.mjs logs --stack=dev-warm
 *   node scripts/platform.mjs scale --stack=prod-scale --worker=3 --worker-fast=2
 */
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  MODULES,
  STACKS,
  buildPlatformSpec,
  parseModuleCsv,
  scaleArgs,
  PLATFORM_LOG_SERVICES,
} from "../deploy/platform-modules.mjs";

const DOCKER_LOG_TAIL = process.env.AUDIT_DOCKER_LOG_TAIL ?? "0";

function parseArgs(argv) {
  /** @type {Record<string, string | boolean>} */
  const flags = {};
  const positional = [];
  for (const arg of argv) {
    if (arg.startsWith("--")) {
      const eq = arg.indexOf("=");
      if (eq === -1) {
        flags[arg.slice(2)] = true;
      } else {
        flags[arg.slice(2, eq)] = arg.slice(eq + 1);
      }
    } else {
      positional.push(arg);
    }
  }
  return { cmd: positional[0], flags, rest: positional.slice(1) };
}

function composeEnv() {
  const env = {
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
  };
  try {
    const raw = readFileSync(join(process.cwd(), ".env"), "utf8").replace(/^\uFEFF/, "");
    for (const line of raw.split(/\r?\n/)) {
      if (!line || line.startsWith("#")) continue;
      const idx = line.indexOf("=");
      if (idx < 1) continue;
      const key = line.slice(0, idx).trim();
      const value = line.slice(idx + 1).trim();
      if (key === "AUDIT_ADMIN_API_TOKEN" && value) {
        env.AUDIT_ADMIN_API_TOKEN = value;
      }
    }
  } catch {
    // optional
  }
  return env;
}

function runDocker(fileArgs, args) {
  const composeArgs = ["compose", ...fileArgs, ...args];
  console.error(`→ docker ${composeArgs.join(" ")}`);
  const result = spawnSync("docker", composeArgs, {
    stdio: "inherit",
    env: composeEnv(),
  });
  process.exit(result.status ?? 1);
}

function printModules() {
  console.log("Platform modules (independently deployable units):\n");
  for (const mod of Object.values(MODULES)) {
    const scale = mod.scalable ? " [scalable]" : "";
    const profiles = mod.profiles?.length ? ` profiles: ${mod.profiles.join(",")}` : "";
    console.log(`  ${mod.id}${scale}`);
    console.log(`    ${mod.label} — ${mod.description}`);
    console.log(`    services: ${mod.services.join(", ")}${profiles}\n`);
  }
}

function printStacks() {
  console.log("Stack presets:\n");
  for (const stack of Object.values(STACKS)) {
    console.log(`  ${stack.id}`);
    console.log(`    ${stack.label}`);
    console.log(`    modules: ${stack.defaultModules.join(", ")}`);
    console.log(`    files: ${stack.files.join(", ")}\n`);
  }
}

const { cmd, flags } = parseArgs(process.argv.slice(2));

if (!cmd || cmd === "help" || flags.help) {
  console.log(`Usage:
  platform modules
  platform stacks
  platform up   --stack=dev-warm --with=obs,errors [--modules-only] [--build] [--detach]
                [--scale-worker=N] [--scale-worker-fast=N]
  platform down --stack=dev-warm --with=obs,errors
  platform logs --stack=dev-warm --with=obs,errors
  platform scale --stack=prod-scale --worker=3 --worker-fast=2

Examples:
  pnpm platform:up -- --stack=dev-warm --with=obs,errors
  pnpm platform:scale -- --worker=3
`);
  process.exit(0);
}

if (cmd === "modules") {
  printModules();
  process.exit(0);
}

if (cmd === "stacks") {
  printStacks();
  process.exit(0);
}

const stack = String(flags.stack ?? "dev");
const withModules = parseModuleCsv(String(flags.with ?? ""));
const modulesOnly = Boolean(flags["modules-only"]);
const spec = buildPlatformSpec({ stack, withModules, modulesOnly });

const profileArgs = spec.profiles.flatMap((p) => ["--profile", p]);

if (cmd === "up") {
  const services = spec.services.filter((s) => !s.startsWith("hatchet-init"));
  const upArgs = [
    ...profileArgs,
    "up",
    "-d",
    ...(flags.build ? ["--build"] : []),
    ...(flags.detach || modulesOnly ? [] : ["--wait"]),
    ...scaleArgs({
      worker: flags["scale-worker"] ? Number(flags["scale-worker"]) : undefined,
      workerFast: flags["scale-worker-fast"]
        ? Number(flags["scale-worker-fast"])
        : undefined,
    }),
    ...services,
  ];
  console.error(`Stack: ${spec.stack} | modules: ${spec.modules.join(", ")}`);
  runDocker(spec.fileArgs, upArgs);
}

if (cmd === "down") {
  runDocker(spec.fileArgs, [...profileArgs, "down"]);
}

if (cmd === "logs") {
  runDocker(spec.fileArgs, [
    ...profileArgs,
    "logs",
    "-f",
    "--timestamps",
    "--tail",
    DOCKER_LOG_TAIL,
    ...PLATFORM_LOG_SERVICES,
  ]);
}

if (cmd === "scale") {
  const worker = flags.worker ? Number(flags.worker) : undefined;
  const workerFast = flags["worker-fast"] ? Number(flags["worker-fast"]) : undefined;
  if (!worker && !workerFast) {
    console.error("Specify --worker=N and/or --worker-fast=N");
    process.exit(1);
  }
  runDocker(spec.fileArgs, [
    ...profileArgs,
    "up",
    "-d",
    "--no-recreate",
    ...scaleArgs({ worker, workerFast }),
    "worker",
    "worker-fast",
  ]);
}

console.error(`Unknown command: ${cmd}`);
process.exit(1);
