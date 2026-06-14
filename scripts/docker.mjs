#!/usr/bin/env node
/**
 * Docker Compose helper — dev vs prod file sets, BuildKit enabled.
 * Usage: node scripts/docker.mjs <command> [extra compose args...]
 *
 * Dev observability (set AUDIT_DEV_OBS env):
 *   none   — default
 *   logs   — Grafana/Loki/Promtail (--profile obs)
 *   traces — logs + Tempo + OTEL (--profile obs --profile obs-traces)
 */
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const SENTRY = ["-f", "compose.sentry.yaml"];

const DEV_NOWARMUP = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.dev.yaml",
  ...SENTRY,
];
const DEV_WARMUP = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.warmup.yaml",
  ...SENTRY,
];
const PROD_CPU = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.prod.yaml",
  ...SENTRY,
];
const PROD_LAN = [...PROD_CPU, "-f", "compose.lan.yaml"];
const PROD_PUBLIC = [...PROD_CPU, "-f", "compose.public.yaml"];
const PROD_CLOUD = [...PROD_PUBLIC, "-f", "compose.cloud.yaml"];
const PROD_CPU_WARMUP = [...PROD_CPU, "-f", "compose.warmup.yaml"];
const PROD_CPU_SCALE = [...PROD_CPU, "-f", "compose.scale.yaml"];
const PROD_GPU = [
  "-f",
  "compose.yaml",
  "-f",
  "compose.cpu.yaml",
  "-f",
  "compose.gpu.yaml",
  "-f",
  "compose.prod.yaml",
];
const OBS = ["-f", "compose.observability.yaml"];
const OBS_TRACES = ["-f", "compose.observability-traces.yaml"];
const GLITCHTIP = ["-f", "compose.glitchtip.yaml"];

const BACKEND_SERVICES = ["api", "worker", "worker-fast"];
const INFRA_SERVICES = ["postgres", "redis", "minio"];
const DEV_STACK = [...INFRA_SERVICES, ...BACKEND_SERVICES];
const PLATFORM_LOG_SERVICES = [
  "web",
  "api",
  "worker",
  "worker-fast",
  "postgres",
  "redis",
  "minio",
  "hatchet-lite",
  "hatchet-postgres",
  "hatchet-init",
];

/** 0 = full container history when attaching; set AUDIT_DOCKER_LOG_TAIL=500 to cap. */
const DOCKER_LOG_TAIL = process.env.AUDIT_DOCKER_LOG_TAIL ?? "0";

/** @returns {"none" | "logs" | "traces"} */
function devObsMode() {
  const mode = process.env.AUDIT_DEV_OBS ?? "none";
  if (mode === "logs" || mode === "traces") return mode;
  return "none";
}

/** @param {string[]} baseFiles */
function withObsFiles(baseFiles) {
  const mode = devObsMode();
  if (mode === "none") return baseFiles;
  const files = [...baseFiles, ...OBS];
  if (mode === "traces") files.push(...OBS_TRACES);
  return files;
}

function obsProfileArgs() {
  const mode = devObsMode();
  const args = [];
  if (mode === "logs" || mode === "traces") args.push("--profile", "obs");
  if (mode === "traces") args.push("--profile", "obs-traces");
  return args;
}

function obsUpArgs() {
  const mode = devObsMode();
  const services = ["loki", "grafana", "promtail"];
  if (mode === "traces") services.push("tempo");
  return [...obsProfileArgs(), "up", "-d", ...services];
}

/** @param {string[]} baseFiles */
function devCommands(baseFiles) {
  const profiles = obsProfileArgs();
  return {
    infra: { baseFiles, args: ["up", "-d", ...INFRA_SERVICES] },
    services: { baseFiles, args: [...profiles, "up", "-d", "--wait", ...BACKEND_SERVICES] },
    "obs:up": { baseFiles, args: obsUpArgs() },
    up: { baseFiles, args: [...profiles, "up", "-d", "--wait", ...DEV_STACK] },
    "up:build": { baseFiles, args: [...profiles, "up", "-d", "--build", ...DEV_STACK] },
    "restart:workers": { baseFiles, args: ["restart", "worker", "worker-fast"] },
    watch: { baseFiles, args: ["watch", ...BACKEND_SERVICES.filter((s) => s !== "api")] },
    down: { baseFiles, args: [...profiles, "down"] },
    logs: {
      baseFiles,
      args: [
        "logs",
        "-f",
        "--timestamps",
        "--tail",
        DOCKER_LOG_TAIL,
        ...PLATFORM_LOG_SERVICES,
      ],
    },
    "logs:platform": {
      baseFiles,
      args: [
        "logs",
        "-f",
        "--timestamps",
        "--tail",
        DOCKER_LOG_TAIL,
        ...PLATFORM_LOG_SERVICES,
      ],
    },
  };
}

const nowarmup = devCommands(DEV_NOWARMUP);
const warmup = Object.fromEntries(
  Object.entries(devCommands(DEV_WARMUP)).map(([key, value]) => [`${key}:warmup`, value])
);

/** @type {Record<string, { baseFiles: string[], args: string[] }>} */
const COMMANDS = {
  ...nowarmup,
  ...warmup,
  "up:web-docker": {
    baseFiles: DEV_NOWARMUP,
    args: ["--profile", "web-docker", "up", "-d", "web"],
  },
  "up:web-docker:warmup": {
    baseFiles: DEV_WARMUP,
    args: ["--profile", "web", "up", "-d", "--wait", ...DEV_STACK, "web"],
  },
  "build:backend": { baseFiles: DEV_NOWARMUP, args: ["build", ...BACKEND_SERVICES] },
  "build:web": { baseFiles: PROD_CPU, args: ["build", "web"] },
  deploy: {
    baseFiles: PROD_CPU,
    args: ["--profile", "web", "up", "-d", "--build"],
  },
  "deploy:lan": {
    baseFiles: PROD_LAN,
    args: ["--profile", "web", "up", "-d", "--force-recreate", "api", "web", "minio"],
  },
  "deploy:public": {
    baseFiles: PROD_PUBLIC,
    args: ["--profile", "web", "up", "-d", "--build"],
  },
  "deploy:cloud": {
    baseFiles: PROD_CLOUD,
    args: ["--profile", "web", "up", "-d", "--build"],
  },
  "deploy:selective": {
    baseFiles: PROD_CPU_WARMUP,
    args: ["--profile", "web", "up", "-d", "--build", "--wait"],
  },
  "down:selective": {
    baseFiles: PROD_CPU_WARMUP,
    args: ["down"],
  },
  "logs:selective": {
    baseFiles: PROD_CPU_WARMUP,
    args: ["logs", "-f", "--timestamps", "--tail", DOCKER_LOG_TAIL, ...PLATFORM_LOG_SERVICES],
  },
  "deploy:scale": {
    baseFiles: PROD_CPU_SCALE,
    args: ["--profile", "web", "up", "-d", "--build", "--scale", "worker=2"],
  },
  "scale:workers": {
    baseFiles: PROD_CPU_SCALE,
    args: ["up", "-d", "--no-recreate", "worker", "worker-fast"],
  },
  "deploy:gpu": {
    baseFiles: PROD_GPU,
    args: ["--profile", "web", "up", "-d", "--build"],
  },
  "deploy:obs": {
    baseFiles: [...PROD_CPU, ...OBS, ...OBS_TRACES],
    args: [
      "--profile",
      "web",
      "--profile",
      "obs",
      "--profile",
      "obs-traces",
      "up",
      "-d",
      "--build",
    ],
  },
  "up:obs": {
    baseFiles: [...DEV_NOWARMUP, ...OBS],
    args: ["--profile", "obs", "up", "-d", ...DEV_STACK],
  },
  "up:obs:traces": {
    baseFiles: [...DEV_NOWARMUP, ...OBS, ...OBS_TRACES],
    args: ["--profile", "obs", "--profile", "obs-traces", "up", "-d", ...DEV_STACK],
  },
  "up:full": {
    baseFiles: [...DEV_NOWARMUP, ...OBS],
    args: ["--profile", "obs", "up", "-d", "--build", ...DEV_STACK],
  },
  "glitchtip:up": {
    baseFiles: GLITCHTIP,
    args: ["--profile", "glitchtip", "up", "-d"],
  },
  "glitchtip:down": {
    baseFiles: GLITCHTIP,
    args: ["--profile", "glitchtip", "down"],
  },
  "deploy:glitchtip": {
    baseFiles: [...PROD_CPU, ...GLITCHTIP],
    args: ["--profile", "web", "--profile", "glitchtip", "up", "-d", "--build"],
  },
};

const PROD_COMMANDS = new Set([
  "deploy",
  "deploy:lan",
  "deploy:public",
  "deploy:cloud",
  "deploy:selective",
  "deploy:scale",
  "deploy:gpu",
  "deploy:obs",
  "build:web",
]);

/** Prefer project .env over stale shell exports (e.g. local-dev-build-token). */
function composeEnv(command) {
  const env = {
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
  };
  if (!PROD_COMMANDS.has(command)) {
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
      if (key === "AUDIT_ADMIN_API_TOKEN" && value) {
        env.AUDIT_ADMIN_API_TOKEN = value;
      }
    }
  } catch {
    // .env is optional for some prod flows; compose will error on missing required vars.
  }
  return env;
}

const [command, ...extra] = process.argv.slice(2);
const template = COMMANDS[command];

if (!template) {
  console.error(`Unknown docker command: ${command ?? "(none)"}`);
  console.error(`Available: ${Object.keys(COMMANDS).join(", ")}`);
  process.exit(1);
}

const spec = {
  files: withObsFiles(template.baseFiles),
  args: [...template.args, ...extra],
};

const composeArgs = ["compose", ...spec.files, ...spec.args];
console.error(`→ docker ${composeArgs.join(" ")}`);

const result = spawnSync("docker", composeArgs, {
  stdio: "inherit",
  env: composeEnv(command),
});

process.exit(result.status ?? 1);
