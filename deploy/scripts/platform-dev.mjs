#!/usr/bin/env node
/**
 * Repody local platform CLI (Windows + macOS + Linux).
 *
 *   pnpm platform setup     # once
 *   pnpm platform           # build images from this checkout + start stack + host NuExtract
 *   pnpm platform dev       # contributors: API + UI from source with reload
 *   pnpm platform status | stop | doctor | logs | help
 *
 * up:  images built from this checkout (docker-bake.hcl, tag "dev"), or the published images
 *      named by REPODY_BACKEND_IMAGE / REPODY_WEB_IMAGE; compose.yaml + compose.portable.yaml
 * dev: compose.yaml data plane + workers built from source; API and UI on the host
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { parseArgs } from "node:util";
import { spawnPrefixed } from "../../scripts/log-prefix.mjs";
import {
  BACKEND_ENV,
  composeArgs as composeArgsFor,
  copyIfMissing,
  fetchProbe,
  findExecutable,
  llamaServe,
  parseEnvFile,
  ROOT,
  resolveExecutable,
  run,
  runtimeEnv,
  setEnvKeys,
  uvBackend,
} from "./runtime-env.mjs";

const AUTH_ENV = path.join(ROOT, ".env.local");
const COMPOSE_ENV_EXAMPLE = path.join(ROOT, "deploy/env/compose.env.example");
const AUTH_ENV_EXAMPLE = path.join(ROOT, "deploy/env.auth.example");
const LLAMA_PATHS = path.join(ROOT, "deploy/llamacpp/paths.local.env");
const LLAMA_MAC_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.mac.env.example");
const LLAMA_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.local.env.example");
// The stack runs the code of this checkout: images are built locally (Docker caches the
// layers, so an unchanged tree rebuilds in seconds). Set both variables to run published
// images instead, e.g. a release from the registry.
const FROM_SOURCE = !process.env.REPODY_BACKEND_IMAGE && !process.env.REPODY_WEB_IMAGE;
const BACKEND_IMAGE = process.env.REPODY_BACKEND_IMAGE || "repody-backend:dev";
const WEB_IMAGE = process.env.REPODY_WEB_IMAGE || "repody-web:dev";

// `pnpm platform -- --flag` may forward the `--` separator itself; it is not an argument here.
const { values: flags, positionals } = parseArgs({
  args: process.argv.slice(2).filter((arg) => arg !== "--"),
  allowPositionals: true,
  options: {
    help: { type: "boolean", short: "h" },
    "platform-only": { type: "boolean" },
    "no-nuextract": { type: "boolean" },
    "no-obs": { type: "boolean" },
    "no-pull": { type: "boolean" },
    "no-build": { type: "boolean" },
  },
});
const command = positionals[0] ?? (flags.help ? "help" : "up");
const isDarwin = process.platform === "darwin";
const isWin = process.platform === "win32";

const opts = {
  platformOnly: Boolean(flags["platform-only"]),
  withNuextract: !(flags["no-nuextract"] || flags["platform-only"]),
  // Observability (Grafana/Loki/Tempo/Bugsink) is on by default.
  withObs: !flags["no-obs"],
  skipPull: Boolean(flags["no-pull"]),
  skipBuild: Boolean(flags["no-build"]),
};

function printHelp() {
  console.log(`
Repody platform CLI (same on Windows, macOS, Linux)

Flow (new PC):
  1) pnpm install && pnpm doctor
  2) Download NuExtract GGUFs → set deploy/llamacpp/paths.local.env
  3) pnpm platform setup     # once — env files + build the images
  4) pnpm platform           # start platform + host NuExtract
  5) pnpm platform status    # health
  6) pnpm platform stop      # tear down

Commands:
  up         Build images from this checkout, start the platform + host NuExtract   [default]
  dev        Contributors: data plane + workers from source, API + UI on the host (reload)
  setup      Once: env / paths + build the images
  bootstrap  setup + up (new machine after git clone / pnpm install)
  doctor     Check everything needed before start (Node, Docker, llama-server, GGUFs, env)
  status     Probe services + observability URLs
  logs       Tail API/web/worker Docker logs
  stop       Stop host NuExtract + Compose
  help       This help

Options (pnpm platform -- … / pnpm platform setup -- …):
  --no-nuextract     Skip host NuExtract (:8081)
  --no-obs           Skip Grafana/Loki/Tempo/Bugsink (on by default)
  --platform-only    Containers only (no host model)
  --no-build         Start the images already built (skip the rebuild)
  --no-pull          Published images only: do not docker pull

Images: ${FROM_SOURCE ? "built from this checkout" : "published"} — ${BACKEND_IMAGE} · ${WEB_IMAGE}
  Published images: REPODY_BACKEND_IMAGE=… REPODY_WEB_IMAGE=… pnpm platform
Guide: docs/LOCAL.md
`);
}

function composeArgs(...parts) {
  return composeArgsFor(["compose.yaml", "compose.portable.yaml"], ...parts);
}

function llamaInstallHint() {
  if (isDarwin) return "brew install llama.cpp";
  if (isWin) return "winget install ggml.llamacpp   (or put llama-server on PATH)";
  return "install llama.cpp so llama-server is on PATH";
}

function copyEnvFiles() {
  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV);
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV);
  const llamaSrc = isDarwin && fs.existsSync(LLAMA_MAC_EXAMPLE) ? LLAMA_MAC_EXAMPLE : LLAMA_EXAMPLE;
  copyIfMissing(llamaSrc, LLAMA_PATHS);
}

/** Point backend/.env at the host model and toggle OTEL for this run (setup / up only). */
function patchBackendEnv() {
  const llamaEnv = parseEnvFile(LLAMA_PATHS);
  setEnvKeys(BACKEND_ENV, {
    AUDIT_LLAMACPP_BASE_URL: "http://127.0.0.1:8081/v1",
    AUDIT_LLAMACPP_SERVED_MODEL:
      (llamaEnv.LLAMACPP_MODEL_ALIAS || "").trim() ||
      process.env.AUDIT_LLAMACPP_SERVED_MODEL ||
      "nuextract3-q8_0",
    // OpenTelemetry agent for containers (Compose reads this file for interpolation).
    OTEL_SDK_DISABLED: opts.withObs ? "false" : "true",
    ...(opts.withObs && { AUDIT_LOG_JSON: "true" }),
  });
}

function nuextractConfigured() {
  const env = parseEnvFile(LLAMA_PATHS);
  const model = (env.LLAMACPP_MODEL || "").trim();
  const mmproj = (env.LLAMACPP_MMPROJ || "").trim();
  if (!model || !fs.existsSync(model)) {
    return {
      ok: false,
      reason: "Set LLAMACPP_MODEL in deploy/llamacpp/paths.local.env to a NuExtract3 .gguf path",
    };
  }
  if (!mmproj || !fs.existsSync(mmproj)) {
    return {
      ok: false,
      reason: "Set LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env to mmproj-NuExtract3*.gguf",
    };
  }
  return { ok: true, reason: `${path.basename(model)} + ${path.basename(mmproj)}` };
}

function checkToolchain() {
  const pnpmBin = isWin ? "pnpm.cmd" : "pnpm";
  const result = spawnSync(process.execPath, [path.join(ROOT, "scripts/check-toolchain.mjs")], {
    cwd: ROOT,
    encoding: "utf8",
    shell: false,
    env: {
      ...process.env,
      // So plain `node … doctor` still sees pnpm when Corepack/PATH is set.
      npm_config_user_agent:
        process.env.npm_config_user_agent ||
        (() => {
          const v = spawnSync(pnpmBin, ["--version"], {
            cwd: ROOT,
            encoding: "utf8",
            shell: isWin,
          });
          const ver = (v.stdout || "").trim();
          return ver ? `pnpm/${ver} node/${process.versions.node}` : undefined;
        })(),
    },
  });
  if (result.status === 0) return { ok: true, detail: (result.stdout || "").trim() || "ok" };
  const detail = (result.stderr || result.stdout || "Node/pnpm mismatch").trim().split(/\r?\n/)[0];
  return { ok: false, detail };
}

function imagesPresent() {
  const missing = [BACKEND_IMAGE, WEB_IMAGE].filter(
    (ref) => spawnSync("docker", ["image", "inspect", ref], { stdio: "ignore" }).status !== 0
  );
  if (missing.length === 0) {
    return {
      ok: true,
      detail: `${BACKEND_IMAGE.split("/").pop()} + ${WEB_IMAGE.split("/").pop()}`,
    };
  }
  if (FROM_SOURCE) return { ok: true, detail: "built from this checkout on start" };
  return { ok: false, detail: `missing ${missing.join(", ")} — run: pnpm platform setup` };
}

/** docker-bake.hcl targets backend + web, loaded into Docker as repody-*:dev. */
function buildImages() {
  console.log("\n── Build images from this checkout (docker buildx bake) ─────────");
  run("docker", ["buildx", "bake", "-f", "docker-bake.hcl", "--load"], {
    inherit: true,
    env: { REPODY_IMAGE_REGISTRY: "", REPODY_IMAGE_TAG: "dev" },
  });
}

function llamaServerVersion(exe) {
  const r = spawnSync(exe, ["--version"], { encoding: "utf8", shell: false, timeout: 15_000 });
  const text = `${r.stdout || ""}${r.stderr || ""}`;
  if (r.status === 0 || text.includes("version")) {
    return { ok: true, detail: (text.trim().split(/\r?\n/)[0] || "ok").slice(0, 80) };
  }
  return { ok: false, detail: "llama-server --version failed" };
}

/**
 * Single preflight for everything needed before starting the platform.
 * Used by `pnpm platform doctor` and automatically by `pnpm platform` / bootstrap.
 * Checks prerequisites (tools, files, images, ports), not that NuExtract loads in VRAM.
 */
function preflight({ quietOk = false } = {}) {
  console.log("\n=== Repody platform preflight ===\n");
  copyEnvFiles();
  const rows = [];
  const toolchain = checkToolchain();
  rows.push({
    name: "Node / pnpm",
    ok: toolchain.ok,
    state: toolchain.detail.replace(/^ok:\s*/i, ""),
    required: true,
    fix: "Install Node 26 (LTS) + npm install --global pnpm@12.16.1",
  });

  const dockerOk = spawnSync("docker", ["info"], { stdio: "ignore" }).status === 0;
  rows.push({
    name: "Docker Desktop",
    ok: dockerOk,
    state: dockerOk ? "ok" : "not running",
    required: true,
    fix: "Start Docker Desktop, wait until ready",
  });

  const images = dockerOk ? imagesPresent() : { ok: false, detail: "docker not running" };
  rows.push({
    name: "Images",
    ok: images.ok,
    state: images.detail,
    required: true,
    fix: "pnpm platform setup",
  });

  const llama = findExecutable("llama-server");
  const llamaRun = llama ? llamaServerVersion(llama) : { ok: false, detail: "missing" };
  rows.push({
    name: "llama-server",
    ok: llamaRun.ok,
    state: llamaRun.ok ? llamaRun.detail : `${llamaRun.detail} — ${llamaInstallHint()}`,
    required: opts.withNuextract,
    fix: llamaInstallHint(),
  });

  const nue = nuextractConfigured();
  rows.push({
    name: "NuExtract3 GGUFs",
    ok: nue.ok,
    state: nue.reason,
    required: opts.withNuextract,
    fix: "Download NuExtract3 + mmproj (pnpm llamacpp:download or https://huggingface.co/numind/NuExtract3-GGUF), then set LLAMACPP_MODEL + LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env",
  });

  for (const [name, file] of [
    ["backend/.env", BACKEND_ENV],
    [".env.local", AUTH_ENV],
  ]) {
    const ok = fs.existsSync(file);
    rows.push({
      name,
      ok,
      state: ok ? "ok" : "missing",
      required: true,
      fix: "pnpm platform setup",
    });
  }

  for (const row of rows) {
    const mark = row.ok ? "ok" : row.required ? "!!" : "--";
    console.log(`  [${mark}] ${row.name.padEnd(18)} ${row.state}`);
  }
  console.log(
    "\nScope: tools, images, NuExtract GGUF files, env. Not checked: VRAM/load success, Keycloak login, extraction E2E.\n"
  );

  const failed = rows.filter((row) => !row.ok && row.required);
  if (failed.length) {
    console.log("Fix required items, then re-run:\n");
    for (const row of failed) console.log(`  • ${row.name}: ${row.fix}`);
    console.log("\nOr: pnpm platform -- --platform-only   # containers only (skip host model)\n");
    process.exit(1);
  }
  if (!quietOk) console.log("Preflight OK — ready to start.\n");
}

function setup() {
  console.log("── Repody platform setup (once) ───────────────────────────────\n");
  copyEnvFiles();
  patchBackendEnv();
  const dockerOk = spawnSync("docker", ["info"], { stdio: "ignore" }).status === 0;
  console.log(`Docker:       ${dockerOk ? "ok" : "NOT RUNNING — start Docker Desktop"}`);
  console.log(
    `llama-server: ${findExecutable("llama-server") || `missing — ${llamaInstallHint()}`}`
  );

  if (!dockerOk) {
    console.warn("\nwarn: skipped the images — start Docker Desktop, then: pnpm platform setup");
  } else if (FROM_SOURCE) {
    buildImages();
  } else if (opts.skipPull) {
    console.log("\n(--no-pull) skipped the image pull");
  } else {
    console.log("\n── Pull published images ──────────────────────────────────────");
    run("docker", ["pull", BACKEND_IMAGE], { inherit: true });
    run("docker", ["pull", WEB_IMAGE], { inherit: true });
  }

  console.log(`
Setup done. Next:
  # Download NuExtract GGUFs (pnpm llamacpp:download) — see deploy/llamacpp/README.md
  # Set LLAMACPP_MODEL + LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env
  pnpm platform
`);
}

async function up() {
  preflight({ quietOk: true });
  patchBackendEnv();
  console.log(
    `Plan: images=${FROM_SOURCE ? "from this checkout" : "published"}  NuExtract=${opts.withNuextract ? "on (host)" : "off"}  Observability=${opts.withObs ? "on" : "off"}`
  );

  if (FROM_SOURCE && !opts.skipBuild) buildImages();
  // Our images (pull_policy on their services): never pulled when built here (a registry has
  // no repody-*:dev) or with --no-pull. Third-party images (Postgres, Keycloak, ...) are pulled
  // when missing: `up --pull` applies to every service, so it stays "missing".
  const pull = FROM_SOURCE || opts.skipPull ? "never" : "missing";
  const composeEnv = {
    REPODY_BACKEND_IMAGE: BACKEND_IMAGE,
    REPODY_WEB_IMAGE: WEB_IMAGE,
    REPODY_PULL_POLICY: process.env.REPODY_PULL_POLICY || pull,
  };
  if (opts.withObs) {
    console.log("\n── Observability (Grafana · Loki · Tempo · Bugsink) ─────────");
    run("docker", composeArgs("--profile", "observability", "up", "-d", "--no-build"), {
      inherit: true,
      allowFail: true,
      env: composeEnv,
    });
  }

  // Host model first so workers never race a cold endpoint; Compose then waits on healthchecks.
  if (opts.withNuextract) {
    console.log("\n── NuExtract (host) ──────────────────────────────────────────");
    llamaServe("serve", { allowFail: true });
  }

  console.log("\n── Start the platform (waits for healthchecks) ───────────────");
  run(
    "docker",
    composeArgs(
      "up",
      "-d",
      "--wait",
      "--wait-timeout",
      "180",
      "--pull",
      "missing",
      "--no-build",
      "postgres",
      "redis",
      "seaweedfs",
      "keycloak",
      "api",
      "web",
      "worker",
      "scheduler"
    ),
    { inherit: true, env: composeEnv }
  );

  await status();
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║  Repody platform — ready                                     ║
╚══════════════════════════════════════════════════════════════╝

  UI          http://localhost:3000
  API         http://localhost:8000
  Keycloak    http://localhost:8080   (admin / admin)
  Sign-in     operator@repody.local / repody-dev
  Extraction  ${opts.withNuextract ? "repody:vlm (NuExtract)" : "(platform only)"}
${
  opts.withObs
    ? `
  Grafana     http://localhost:3030   (anon Admin — Loki/Tempo)
  Bugsink     http://localhost:8090   (admin@repody.local / repody-dev)
              Create a project → set BUGSINK_DSN in backend/.env → recreate api
`
    : ""
}
  Use localhost (not 127.0.0.1) in the browser for auth.

  pnpm platform status
  pnpm platform logs      # tail API / web / workers
  pnpm platform stop
`);
}

/**
 * Contributor mode: Compose runs the data plane and builds the workers from source; the API
 * (uvicorn) and UI (next dev) run on the host so edits reload. Ctrl+C stops API + UI only.
 */
async function dev() {
  copyEnvFiles();
  patchBackendEnv();
  if (opts.withObs) {
    run("docker", composeArgsFor(["compose.yaml"], "--profile", "observability", "up", "-d"), {
      inherit: true,
      allowFail: true,
    });
  }
  if (opts.withNuextract) llamaServe("serve", { allowFail: true });

  console.log("\n── Data plane + workers (built from source) ──────────────────");
  // Build first: --wait-timeout would otherwise also count the image build.
  run("docker", composeArgsFor(["compose.yaml"], "--profile", "workers", "build"), {
    inherit: true,
  });
  run(
    "docker",
    composeArgsFor(
      ["compose.yaml"],
      "--profile",
      "workers",
      "up",
      "-d",
      "--wait",
      "--wait-timeout",
      "300",
      "postgres",
      "redis",
      "seaweedfs",
      "keycloak",
      "worker",
      "scheduler"
    ),
    { inherit: true }
  );
  run(...uvBackend(["alembic", "upgrade", "head"]), { inherit: true });

  // backend/.env wins over the shell so a leftover AUDIT_DATABASE_URL (pytest) cannot leak in.
  const apiEnv = { ...process.env, ...parseEnvFile(BACKEND_ENV) };
  // With observability, run the API under the OpenTelemetry agent like the containers do.
  const apiArgs = ["run", "--extra", "otel"];
  if (opts.withObs) {
    apiArgs.push("opentelemetry-instrument");
    Object.assign(apiEnv, {
      OTEL_SERVICE_NAME: "repody-api",
      OTEL_EXPORTER_OTLP_ENDPOINT: "http://127.0.0.1:4318",
      OTEL_EXPORTER_OTLP_PROTOCOL: "http/protobuf",
      OTEL_METRICS_EXPORTER: "none",
      OTEL_LOGS_EXPORTER: "none",
    });
  }
  apiArgs.push("uvicorn", "repody.main:app", "--port", "8000");
  // Uvicorn's reloader is unreliable on Windows; opt in with REPODY_DEV_API_RELOAD=1.
  if (!isWin || process.env.REPODY_DEV_API_RELOAD === "1") apiArgs.push("--reload");
  const children = [
    spawnPrefixed("api", resolveExecutable("uv"), apiArgs, {
      cwd: path.join(ROOT, "backend"),
      env: apiEnv,
    }),
    spawnPrefixed(
      "ui",
      process.execPath,
      [path.join(ROOT, "node_modules/next/dist/bin/next"), "dev"],
      { cwd: ROOT, env: runtimeEnv(path.join(ROOT, ".env"), AUTH_ENV) }
    ),
  ];
  console.log(`
  UI   http://localhost:3000   (operator@repody.local / repody-dev)
  API  http://localhost:8000/docs

  Ctrl+C stops API + UI; \`pnpm platform stop\` stops the containers.
`);
  const stopChildren = () => {
    for (const child of children) child.kill("SIGTERM");
  };
  process.on("SIGINT", stopChildren);
  process.on("SIGTERM", stopChildren);
  const code = await Promise.race(
    children.map((child) => new Promise((resolve) => child.on("exit", (c) => resolve(c ?? 0))))
  );
  stopChildren();
  process.exit(code);
}

async function status() {
  const checks = [
    ["API", "http://127.0.0.1:8000/v1/healthz"],
    ["UI", "http://127.0.0.1:3000"],
    ["Keycloak", "http://127.0.0.1:8080"],
    ["NuExtract", "http://127.0.0.1:8081/v1/models"],
    ["Grafana", "http://127.0.0.1:3030"],
    ["Bugsink", "http://127.0.0.1:8090"],
  ];
  console.log("\n=== Repody platform status ===\n");
  for (const [name, url] of checks) {
    const { ok } = await fetchProbe(url, 2500);
    console.log(`  [${ok ? "ok" : "--"}] ${name.padEnd(10)} ${url}`);
  }
  console.log("\n  Logs:  pnpm platform logs");
  console.log('  Grafana Explore → Loki {container=~"repody-.*"}\n');
}

function logs() {
  console.log("Tailing API + web + workers (Ctrl+C to stop)…\n");
  run(
    "docker",
    composeArgs(
      "--profile",
      "workers",
      "logs",
      "-f",
      "--tail",
      "200",
      "api",
      "web",
      "worker",
      "scheduler"
    ),
    { inherit: true, allowFail: true }
  );
}

function stop() {
  console.log("Stopping host NuExtract + Hub Compose stack…");
  llamaServe("stop", { allowFail: true });
  run(
    "docker",
    composeArgs("--profile", "workers", "--profile", "observability", "down", "--remove-orphans"),
    { inherit: true, allowFail: true }
  );
  console.log("Stopped. Start again with: pnpm platform");
}

const commands = {
  help: printHelp,
  setup,
  bootstrap: async () => {
    setup();
    await up();
  },
  doctor: () => preflight(),
  up,
  dev,
  status,
  logs,
  stop,
};
if (flags.help) printHelp();
else if (commands[command]) await commands[command]();
else {
  console.error(`Unknown command: ${command}\n`);
  printHelp();
  process.exit(2);
}
