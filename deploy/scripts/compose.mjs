#!/usr/bin/env node
/**
 * Unified Docker Compose CLI — stacks, modules, recipes.
 * @see deploy/platform-modules.mjs
 * @see DEPLOY.md
 */
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { COMPOSE } from "../compose-paths.mjs";
import {
  MODULES,
  STACKS,
  buildPlatformSpec,
  parseModuleCsv,
  parseOverlayFlags,
  scaleArgs,
  PLATFORM_LOG_SERVICES,
  INFRA_SERVICES,
  BACKEND_SERVICES,
  HATCHET_INIT_PROFILE,
  PROD_STACK_IDS,
} from "../platform-modules.mjs";
import { printPlatformBanner } from "./platform-urls.mjs";
import { dockerComposeRootArgs } from "./compose-docker-args.mjs";

const DOCKER_LOG_TAIL = process.env.AUDIT_DOCKER_LOG_TAIL ?? "0";

/** @returns {"none" | "logs" | "traces"} */
function devObsMode() {
  const mode = process.env.AUDIT_DEV_OBS ?? "none";
  if (mode === "logs" || mode === "traces") return mode;
  return "none";
}

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
        const key = arg.slice(2, eq);
        const value = arg.slice(eq + 1);
        if (key === "with" && typeof flags.with === "string" && flags.with.length > 0) {
          flags.with = `${flags.with},${value}`;
        } else {
          flags[key] = value;
        }
      }
    } else {
      positional.push(arg);
    }
  }
  return { cmd: positional[0], sub: positional[1], flags, rest: positional.slice(2) };
}

function composeEnv(stack) {
  const env = {
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
  };
  if (!PROD_STACK_IDS.has(stack)) {
    return env;
  }
  try {
    const raw = readFileSync(join(process.cwd(), ".env"), "utf8").replace(/^\uFEFF/, "");
    for (const line of raw.split(/\r?\n/)) {
      if (!line || line.startsWith("#")) continue;
      const idx = line.indexOf("=");
      if (idx < 1) continue;
      const key = line.slice(0, idx).trim();
      const value = line.slice(idx + 1).trim();
      if (key === "AUTH_SECRET" && value) {
        env.AUTH_SECRET = value;
      }
      if (key === "AUTH_KEYCLOAK_CLIENT_SECRET" && value) {
        env.AUTH_KEYCLOAK_CLIENT_SECRET = value;
      }
      if (key === "AUDIT_OIDC_ISSUER" && value) {
        env.AUDIT_OIDC_ISSUER = value;
      }
    }
  } catch {
    // optional
  }
  return env;
}

function runDocker(fileArgs, args, stack) {
  const composeArgs = ["compose", ...dockerComposeRootArgs(), ...fileArgs, ...args];
  console.error(`→ docker ${composeArgs.join(" ")}`);
  const result = spawnSync("docker", composeArgs, {
    stdio: "inherit",
    env: composeEnv(stack),
  });
  process.exit(result.status ?? 1);
}

function resolveSpec(stackId, withCsv, modulesOnly, overlays) {
  const withModules = parseModuleCsv(withCsv);
  let spec = buildPlatformSpec({
    stack: stackId,
    withModules,
    modulesOnly,
    overlays,
  });

  const obsMode = devObsMode();
  if (spec.stack === "dev" && obsMode !== "none" && !modulesOnly) {
    const extraFiles = [COMPOSE.observability];
    const extraProfiles = ["obs"];
    if (obsMode === "traces") {
      extraFiles.push(COMPOSE.observabilityTraces);
      extraProfiles.push("obs-traces");
    }
    const filePaths = [...spec.filePaths];
    for (const f of extraFiles) {
      if (!filePaths.includes(f)) filePaths.push(f);
    }
    const profiles = [...spec.profiles];
    for (const p of extraProfiles) {
      if (!profiles.includes(p)) profiles.push(p);
    }
    spec = {
      ...spec,
      filePaths,
      fileArgs: filePaths.flatMap((p) => ["-f", p]),
      profiles,
    };
  }

  return spec;
}

function profileArgs(profiles, extra) {
  const set = new Set([HATCHET_INIT_PROFILE, ...profiles, ...(extra ?? [])]);
  return [...set].flatMap((p) => ["--profile", p]);
}

function authServicesFor(spec) {
  return spec.modules.includes("auth") ? [...MODULES.auth.services] : [];
}

function servicesForOnly(only, spec) {
  if (!only) {
    return spec.services.filter((s) => s !== "hatchet-init");
  }
  switch (only) {
    case "infra":
      return [...INFRA_SERVICES, ...authServicesFor(spec)];
    case "services":
    case "backend":
      return [...BACKEND_SERVICES];
    case "workers":
      return ["worker", "worker-fast"];
    case "web":
      return ["web"];
    case "obs": {
      const services = [...MODULES.obs.services];
      if (spec.modules.includes("traces")) {
        services.push(...MODULES.traces.services);
      }
      return services;
    }
    default:
      throw new Error(
        `Unknown --only=${only}. Use: infra, services, backend, workers, web, obs`
      );
  }
}

function printHelp() {
  console.log(`Repody Compose CLI

  compose stacks | modules | help
  compose recipe dev | prod | stop  [flags]
  compose urls   --stack=STACK [options]
  compose up   --stack=STACK [options]
  compose down --stack=STACK
  compose logs --stack=STACK [-- SERVICE ...]
  compose ps   --stack=STACK [-- SERVICE ...]
  compose scale --stack=prod --scale --worker=N
  compose build --stack=STACK [--only=api|worker|web|backend]
  compose restart workers --stack=STACK
  compose watch --stack=dev

Stacks: dev, prod, prod-micro, vps, gpu, e2e

Stack overlays (combine with --stack):
  --warmup   OCR model warmup — Repody VLM (dev: enables warmup overlay)
  --lan      Office LAN (after pnpm configure:lan)
  --public   HTTPS via Caddy
  --scale    Horizontal worker pool tuning

Examples:
  pnpm dev                          # recipe: host Next + Docker backend
  pnpm dev -- --warmup --logs
  pnpm prod -- --warmup --detach
  pnpm compose up --stack=prod --build
  pnpm compose up --stack=prod --public --build
  pnpm compose up --stack=vps --with=obs,traces --build
  pnpm compose up --modules-only --with=bugsink --detach
  pnpm compose urls --stack=dev --logs

Options for up:
  --build --wait --modules-only
  --with=obs,traces,bugsink
  --only=infra|services|workers|web|obs
  --scale-worker=N --scale-worker-fast=N
  --force-recreate=a,b,c
`);
}

function printModules() {
  console.log("Platform modules:\n");
  for (const mod of Object.values(MODULES)) {
    const scale = mod.scalable ? " [scalable]" : "";
    const profiles = mod.profiles?.length ? ` profiles: ${mod.profiles.join(",")}` : "";
    console.log(`  ${mod.id}${scale}`);
    console.log(`    ${mod.label} — ${mod.description}`);
    console.log(`    services: ${mod.services.join(", ")}${profiles}\n`);
  }
}

function printStacks() {
  console.log("Stack presets (use overlays: --warmup, --lan, --public, --scale):\n");
  for (const stack of Object.values(STACKS)) {
    if (!stack.files.length) continue;
    console.log(`  ${stack.id}`);
    console.log(`    ${stack.label}`);
    console.log(`    modules: ${stack.defaultModules.join(", ")}`);
    console.log(`    files: ${stack.files.join(", ")}\n`);
  }
}

const { cmd, sub, flags, rest } = parseArgs(process.argv.slice(2));

if (!cmd || cmd === "help" || flags.help) {
  printHelp();
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

if (cmd === "recipe") {
  if (!sub) {
    console.error("Usage: compose recipe <dev|prod|stop> [flags]");
    process.exit(1);
  }
  const { runRecipe } = await import("./compose-recipes.mjs");
  runRecipe(sub, process.argv.slice(3));
} else if (cmd === "urls") {
  const urlStack = String(flags.stack ?? "dev");
  const withModules = parseModuleCsv(String(flags.with ?? ""));
  const urlOverlays = parseOverlayFlags(flags);
  printPlatformBanner({
    mode: urlStack === "vps" ? "vps" : urlStack === "dev" ? "dev" : "prod",
    logs: withModules.includes("obs") || devObsMode() !== "none",
    traces: withModules.includes("traces") || devObsMode() === "traces",
    publicHttps: Boolean(urlOverlays.public) || urlStack === "vps",
    lan: Boolean(urlOverlays.lan),
    publicDomain: process.env.PUBLIC_DOMAIN,
    filesDomain: process.env.FILES_DOMAIN,
    publicHost: process.env.PUBLIC_HOST,
  });
} else {
let overlays = parseOverlayFlags(flags);
const stack = String(flags.stack ?? (cmd === "up" && flags["modules-only"] ? "dev" : "dev"));
const withCsv = String(flags.with ?? "");
const modulesOnly = Boolean(flags["modules-only"]);

if (cmd === "scale") {
  overlays = { ...overlays, scale: true };
}

const spec = resolveSpec(stack, withCsv, modulesOnly, overlays);

const extraProfiles = flags.profile
  ? String(flags.profile)
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
  : [];

if (cmd === "up") {
  const only = flags.only ? String(flags.only) : undefined;
  const services = servicesForOnly(only, spec);
  const profiles = profileArgs(spec.profiles, extraProfiles);
  if (only === "web" && !extraProfiles.length && spec.stack === "dev") {
    profiles.push("--profile", "web-docker");
  }

  const shouldWait =
    Boolean(flags.wait) ||
    only === "services" ||
    (!only && !modulesOnly && !flags.build && spec.stack === "dev");

  const upArgs = [
    ...profiles,
    "up",
    "-d",
    ...(flags.build ? ["--build"] : []),
    ...(shouldWait ? ["--wait"] : []),
    ...scaleArgs({
      worker: flags["scale-worker"] ? Number(flags["scale-worker"]) : undefined,
      workerFast: flags["scale-worker-fast"]
        ? Number(flags["scale-worker-fast"])
        : undefined,
    }),
  ];

  if (flags["force-recreate"]) {
    upArgs.push("--force-recreate", ...String(flags["force-recreate"]).split(","));
  }

  upArgs.push(...services);
  const overlayNote = Object.entries(spec.overlays ?? {})
    .filter(([, v]) => v)
    .map(([k]) => k)
    .join(",");
  console.error(
    `Stack: ${spec.stack}${overlayNote ? ` (+${overlayNote})` : ""} | modules: ${spec.modules.join(", ")}`
  );
  runDocker(spec.fileArgs, upArgs, spec.stack);
}

if (cmd === "down") {
  const downArgs = [...profileArgs(spec.profiles, extraProfiles), "down"];
  if (flags.volumes) downArgs.push("-v");
  if (flags["remove-orphans"]) downArgs.push("--remove-orphans");
  runDocker(spec.fileArgs, downArgs, spec.stack);
}

if (cmd === "logs") {
  const logServices = rest.length ? rest : PLATFORM_LOG_SERVICES;
  runDocker(
    spec.fileArgs,
    [
      ...profileArgs(spec.profiles, extraProfiles),
      "logs",
      "-f",
      "--timestamps",
      "--tail",
      DOCKER_LOG_TAIL,
      ...logServices,
    ],
    spec.stack
  );
}

if (cmd === "ps") {
  runDocker(
    spec.fileArgs,
    [...profileArgs(spec.profiles, extraProfiles), "ps", ...rest],
    spec.stack
  );
}

if (cmd === "scale") {
  const worker = flags.worker ? Number(flags.worker) : undefined;
  const workerFast = flags["worker-fast"] ? Number(flags["worker-fast"]) : undefined;
  if (!worker && !workerFast) {
    console.error("Specify --worker=N and/or --worker-fast=N");
    process.exit(1);
  }
  runDocker(
    spec.fileArgs,
    [
      ...profileArgs(spec.profiles, extraProfiles),
      "up",
      "-d",
      "--no-recreate",
      ...scaleArgs({ worker, workerFast }),
      "worker",
      "worker-fast",
    ],
    spec.stack
  );
}

if (cmd === "build") {
  const only = flags.only ? String(flags.only) : "backend";
  let targets;
  switch (only) {
    case "api":
      targets = ["api"];
      break;
    case "worker":
      targets = ["worker", "worker-fast"];
      break;
    case "web":
      targets = ["web"];
      break;
    case "backend":
      targets = [...BACKEND_SERVICES];
      break;
    default:
      console.error(`Unknown --only=${only}. Use: api, worker, web, backend`);
      process.exit(1);
  }
  runDocker(
    spec.fileArgs,
    [...profileArgs(spec.profiles, extraProfiles), "build", ...targets],
    spec.stack
  );
}

if (cmd === "restart") {
  if (sub !== "workers") {
    console.error("Usage: compose restart workers --stack=STACK");
    process.exit(1);
  }
  runDocker(spec.fileArgs, ["restart", "worker", "worker-fast"], spec.stack);
}

if (cmd === "watch") {
  runDocker(
    spec.fileArgs,
    ["watch", ...BACKEND_SERVICES.filter((s) => s !== "api")],
    spec.stack
  );
}

console.error(`Unknown command: ${cmd}`);
printHelp();
process.exit(1);
}
