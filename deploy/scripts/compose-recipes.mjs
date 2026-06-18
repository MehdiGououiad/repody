#!/usr/bin/env node
/**
 * High-level workflows: pnpm dev | pnpm prod | pnpm stop
 */
import { spawn, spawnSync, execSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { spawnPrefixed } from "../../scripts/log-prefix.mjs";
import { printPlatformBanner } from "./platform-urls.mjs";
import { loadRepoEnv } from "./load-repo-env.mjs";
import { STACKS } from "../platform-modules.mjs";

const COMPOSE_CLI = join(process.cwd(), "deploy/scripts/compose.mjs");
const VALID_MODELS = new Set(["repody-vlm"]);

/** @param {string} name @param {string[]} argv */
export function runRecipe(name, argv) {
  switch (name) {
    case "dev":
      runDevHostFrontend(argv.includes("--warmup"), argv);
      return;
    case "prod":
      runContainerStack(argv);
      return;
    case "stop":
      runStop(argv);
      return;
    default:
      console.error(`Unknown recipe: ${name}`);
      console.error("Available: dev, prod, stop");
      process.exit(1);
  }
}

/** @param {string[]} args */
function composeArgs(...args) {
  return [COMPOSE_CLI, ...args];
}

/** Node argv arrays are dropped on Windows when shell:true (DEP0190). */
function spawnUsesShell(command) {
  if (process.platform !== "win32") return false;
  const base = command.replace(/\\/g, "/").split("/").pop()?.toLowerCase();
  return base !== "node" && base !== "node.exe";
}

function runSync(label, command, args, env = process.env) {
  console.error(`\n▶ ${label}\n`);
  const result = spawnSync(command, args, {
    stdio: "inherit",
    shell: spawnUsesShell(command),
    env,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function killProcessTree(pid) {
  if (!pid) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/T", "/F", "/PID", String(pid)], {
      shell: true,
      stdio: "ignore",
    });
    return;
  }
  try {
    process.kill(-pid, "SIGTERM");
  } catch {
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      // already exited
    }
  }
}

function stopChild(proc) {
  if (!proc || proc.killed || proc.exitCode != null) return;
  killProcessTree(proc.pid);
}

function envFileIsNewerThanBuild() {
  const buildIdPath = join(process.cwd(), ".next", "BUILD_ID");
  if (!existsSync(buildIdPath)) return true;
  const buildMtime = statSync(buildIdPath).mtimeMs;
  for (const file of [".env", ".env.local"]) {
    const path = join(process.cwd(), file);
    if (existsSync(path) && statSync(path).mtimeMs > buildMtime) {
      return true;
    }
  }
  return false;
}

/** @param {boolean} warmup @param {string[]} argv */
function runDevHostFrontend(warmup, argv) {
  const forceRebuild = argv.includes("--rebuild");
  const withTraces = argv.includes("--traces");
  const withLogs = argv.includes("--logs") || withTraces;
  const withAuth = argv.includes("--auth");
  const withLan = argv.includes("--lan");
  const overlayArgs = [...(warmup ? ["--warmup"] : []), ...(withLan ? ["--lan"] : [])];
  const authModuleArgs = withAuth ? ["--with=auth"] : [];
  const buildIdPath = join(process.cwd(), ".next", "BUILD_ID");
  const standaloneServerPath = join(
    process.cwd(),
    ".next",
    "standalone",
    "server.js"
  );

  /** @type {import("node:child_process").ChildProcess | null} */
  let webProcess = null;
  /** @type {import("node:child_process").ChildProcess | null} */
  let logsProcess = null;
  let stackStarted = false;
  let shuttingDown = false;

  const childEnv = loadRepoEnv({
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
    BACKEND_URL: process.env.BACKEND_URL ?? "http://127.0.0.1:8000",
    AUDIT_WARM_MODELS: process.env.AUDIT_WARM_MODELS ?? "repody-vlm",
    AUDIT_COMPOSE_STACK: "dev",
    AUDIT_COMPOSE_WARMUP: warmup ? "1" : "0",
    AUDIT_DEV_OBS: withTraces ? "traces" : withLogs ? "logs" : "none",
  });

  if (withAuth && !childEnv.AUTH_SECRET) {
    console.error(
      "\n✗ --auth requires AUTH_SECRET in .env or .env.local (e.g. openssl rand -base64 32)\n"
    );
    process.exit(1);
  }

  if (withAuth) {
    if (withLan) {
      if (!childEnv.PUBLIC_HOST) {
        console.error(
          "\n✗ --lan requires PUBLIC_HOST in .env — run: pnpm configure:lan\n"
        );
        process.exit(1);
      }
      const host = childEnv.PUBLIC_HOST;
      childEnv.AUTH_URL = `http://${host}:3000`;
      childEnv.AUTH_KEYCLOAK_ISSUER = `http://${host}:8080/realms/repody`;
      childEnv.AUDIT_OIDC_ISSUER = `http://${host}:8080/realms/repody`;
      childEnv.KEYCLOAK_HOSTNAME = host;
    } else {
      childEnv.AUTH_URL = "http://localhost:3000";
      childEnv.AUTH_KEYCLOAK_ISSUER = "http://127.0.0.1:8080/realms/repody";
      childEnv.AUDIT_OIDC_ISSUER = "http://127.0.0.1:8080/realms/repody";
      childEnv.KEYCLOAK_HOSTNAME = "127.0.0.1";
    }
    childEnv.AUTH_KEYCLOAK_ID ??= "repody-web";
    childEnv.AUTH_KEYCLOAK_SECRET ??= "repody-web-dev-secret";
    childEnv.AUDIT_OIDC_JWKS_URL ??=
      "http://keycloak:8080/realms/repody/protocol/openid-connect/certs";
  }

  const bugsinkModuleArgs =
    childEnv.BUGSINK_DSN || childEnv.NEXT_PUBLIC_BUGSINK_DSN
      ? ["--with=bugsink"]
      : [];

  const composeWithModules = [
    ...(withAuth ? ["auth"] : []),
    ...(bugsinkModuleArgs.length ? ["bugsink"] : []),
  ];
  if (composeWithModules.length) {
    childEnv.AUDIT_COMPOSE_WITH = composeWithModules.join(",");
  }

  const needsBugsinkRebuild =
    Boolean(childEnv.NEXT_PUBLIC_BUGSINK_DSN) && envFileIsNewerThanBuild();

  function stopDocker() {
    if (!stackStarted) return;
    console.error("\n▶ Stopping Docker stack…\n");
    spawnSync("node", composeArgs("down", "--stack=dev", ...overlayArgs), {
      stdio: "inherit",
      shell: false,
      env: childEnv,
    });
    stackStarted = false;
  }

  function shutdown(reason) {
    if (shuttingDown) return;
    shuttingDown = true;
    console.error(`\n▶ Shutting down platform (${reason})…`);
    stopChild(webProcess);
    webProcess = null;
    stopChild(logsProcess);
    logsProcess = null;
    stopDocker();
    process.exit(0);
  }

  process.on("SIGINT", () => shutdown("Ctrl+C"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));

  if (withLogs) {
    const obsWith = withTraces ? "obs,traces" : "obs";
    runSync(
      withTraces
        ? "Starting observability (Grafana/Loki + Tempo/OTEL)"
        : "Starting observability (Grafana/Loki — no traces)",
      "node",
      [
        ...composeArgs(
          "up",
          "--stack=dev",
          ...overlayArgs,
          ...authModuleArgs,
          `--with=${obsWith}`,
          "--only=obs",
          "--detach"
        ),
      ],
      childEnv
    );
  }

  runSync(
    "Starting infra (postgres, redis, minio, hatchet)",
    "node",
    [...composeArgs("up", "--stack=dev", ...overlayArgs, ...authModuleArgs, ...bugsinkModuleArgs, "--only=infra")],
    childEnv
  );

  stackStarted = true;

  if (warmup) {
    runSync(
      "Preparing Repody VLM in Docker Model Runner",
      "node",
      ["scripts/prepare-repody-vlm-model.mjs"],
      childEnv
    );
  }

  runSync(
    warmup
      ? "Starting backend with OCR model warmup enabled (Repody VLM)"
      : "Starting backend without warmup (fast boot)",
    "node",
    [...composeArgs("up", "--stack=dev", ...overlayArgs, ...authModuleArgs, ...bugsinkModuleArgs, "--only=services")],
    childEnv
  );

  runSync("Waiting for API health", "node", ["scripts/wait-for-api.mjs"], childEnv);

  if (warmup) {
    runSync(
      "Waiting for OCR worker warmup",
      "node",
      ["scripts/wait-for-warmup.mjs"],
      { ...childEnv, AUDIT_COMPOSE_WARMUP: "1" }
    );
  }

  if (forceRebuild || needsBugsinkRebuild || !existsSync(buildIdPath)) {
    if (forceRebuild) {
      runSync(
        "Preparing clean Next.js rebuild",
        "node",
        ["scripts/clean-next-for-rebuild.mjs"],
        childEnv
      );
    } else if (needsBugsinkRebuild) {
      console.error(
        "\n▶ Rebuilding Next.js — NEXT_PUBLIC_BUGSINK_DSN changed (required for browser error reporting).\n"
      );
    }
    runSync("Building Next.js (production)", "pnpm", ["build"], childEnv);
  } else {
    console.error(
      "\n▶ Using existing production build (.next). Run with --rebuild to rebuild.\n"
    );
  }

  runSync(
    "Preparing standalone server",
    "node",
    ["scripts/prepare-standalone.mjs"],
    childEnv
  );

  const obsLines = withLogs
    ? withTraces
      ? "Grafana + Tempo enabled — see endpoint list below"
      : "Grafana/Loki enabled — see endpoint list below"
    : "";
  const authLine = withAuth
    ? withLan
      ? `Keycloak http://${childEnv.PUBLIC_HOST}:8080 — operator@repody.local / repody-dev`
      : "Keycloak http://127.0.0.1:8080 — operator@repody.local / repody-dev"
    : "";
  printPlatformBanner({
    mode: "dev",
    lan: withLan,
    publicHost: childEnv.PUBLIC_HOST,
    logs: withLogs,
    traces: withTraces,
    footer: [
      "Docker logs: api, worker, worker-fast, postgres, redis, minio, hatchet",
      obsLines,
      authLine,
      childEnv.NEXT_PUBLIC_BUGSINK_DSN || childEnv.BUGSINK_DSN
        ? "Bugsink DSN configured — see docs/BUGSINK.md"
        : "",
      "Ctrl+C: stop web + logs + docker compose down",
    ]
      .filter(Boolean)
      .join(" · "),
  });

  console.error("Streaming logs (source of truth)…\n");

  logsProcess = spawn(
    "node",
    composeArgs("logs", "--stack=dev", ...overlayArgs, ...authModuleArgs, ...bugsinkModuleArgs),
    {
      stdio: "inherit",
      shell: false,
      env: childEnv,
      cwd: process.cwd(),
    }
  );

  logsProcess.on("exit", () => {
    logsProcess = null;
    if (!shuttingDown) shutdown("docker logs exited");
  });

  webProcess = spawnPrefixed("web", process.execPath, [standaloneServerPath], {
    env: {
      ...childEnv,
      PORT: childEnv.PORT ?? "3000",
      HOSTNAME: withLan ? "0.0.0.0" : (childEnv.HOSTNAME ?? "0.0.0.0"),
      AUTH_URL: childEnv.AUTH_URL ?? childEnv.NEXTAUTH_URL ?? "http://localhost:3000",
    },
    cwd: join(process.cwd(), ".next", "standalone"),
  });

  webProcess.on("exit", (code, signal) => {
    if (shuttingDown) return;
    shutdown(signal ? String(signal) : `web exited (${code ?? 0})`);
  });
}

function modelList(argv) {
  const option = argv.find((arg) => arg.startsWith("--models="));
  const raw = option?.slice("--models=".length) ?? "repody-vlm";
  const models = [
    ...new Set(
      raw
        .split(",")
        .map((value) => value.trim().toLowerCase())
        .filter(Boolean)
    ),
  ];
  const invalid = models.filter((model) => !VALID_MODELS.has(model));
  if (invalid.length) {
    console.error(`Unknown warmup model(s): ${invalid.join(", ")}`);
    process.exit(1);
  }
  return models;
}

/** @param {string[]} argv */
function runContainerStack(argv) {
  const models = modelList(argv);
  const selected = new Set(models);
  const detached = argv.includes("--detach");
  const warmup =
    argv.includes("--warmup") ||
    argv.includes("--warm") ||
    models.length > 0;
  const overlayArgs = warmup ? ["--warmup"] : [];
  const env = {
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
    AUDIT_WARM_MODELS: models.join(","),
    AUDIT_WARM_REPODY_VLM: String(selected.has("repody-vlm")),
  };

  if (selected.has("repody-vlm")) {
    runSync(
      "Preparing Repody VLM",
      "node",
      ["scripts/prepare-repody-vlm-model.mjs"],
      env
    );
  }

  runSync(
    "Starting production stack",
    "node",
    [
      ...composeArgs(
        "up",
        "--stack=prod",
        ...overlayArgs,
        "--build",
        "--wait"
      ),
    ],
    env
  );

  if (warmup && models.length) {
    runSync(
      "Waiting for OCR worker warmup",
      "node",
      ["scripts/wait-for-warmup.mjs"],
      { ...env, AUDIT_COMPOSE_STACK: "prod", AUDIT_COMPOSE_WARMUP: "1" }
    );
  }

  if (!detached) {
    printPlatformBanner({
      mode: "prod",
      publicHttps: argv.includes("--public"),
      lan: argv.includes("--lan"),
      publicDomain: process.env.PUBLIC_DOMAIN,
      filesDomain: process.env.FILES_DOMAIN,
      publicHost: process.env.PUBLIC_HOST,
      footer: "Streaming logs · Ctrl+C ends log stream · pnpm stop to tear down",
    });
    runSync(
      "Streaming logs",
      "node",
      [...composeArgs("logs", "--stack=prod", ...overlayArgs)],
      env
    );
  } else {
    printPlatformBanner({
      mode: "prod",
      publicHttps: argv.includes("--public"),
      lan: argv.includes("--lan"),
      publicDomain: process.env.PUBLIC_DOMAIN,
      filesDomain: process.env.FILES_DOMAIN,
      publicHost: process.env.PUBLIC_HOST,
      footer: "Detached mode — containers keep running · pnpm stop to tear down",
    });
  }
}

/** Host processes started outside Docker (pnpm dev web, pnpm dev:api). */
const HOST_DEV_PORTS = [3000, 8000];

/** Compose `down` variants — cover overlays/modules used by dev recipes. */
const DEV_DOWN_ARGS = [
  [],
  ["--warmup"],
  ["--lan"],
  ["--warmup", "--lan"],
  ["--with=auth"],
  ["--warmup", "--with=auth"],
  ["--lan", "--with=auth"],
  ["--warmup", "--lan", "--with=auth"],
  ["--with=bugsink"],
  ["--warmup", "--with=bugsink"],
  ["--with=obs"],
  ["--with=obs,traces"],
  ["--warmup", "--with=auth", "--with=bugsink"],
  ["--warmup", "--with=auth", "--with=obs,traces"],
];

const DEV_MODULE_ONLY_DOWN_ARGS = [
  ["--modules-only", "--with=obs"],
  ["--modules-only", "--with=obs,traces"],
  ["--modules-only", "--with=bugsink"],
  ["--modules-only", "--with=auth"],
];

/** Stacks that may be running outside `pnpm dev`. */
const PLATFORM_STACK_DOWN = [
  { stack: "prod", args: [[]] },
  { stack: "prod", args: [["--warmup"], ["--public"], ["--lan"], ["--warmup", "--public"]] },
  { stack: "prod-micro", args: [[]] },
  { stack: "e2e", args: [[]] },
  { stack: "gpu", args: [[], ["--warmup"]] },
  { stack: "vps", args: [[], ["--with=obs,traces"]] },
];

function composeDown(args, env, { quiet = true } = {}) {
  const result = spawnSync("node", composeArgs("down", "--remove-orphans", ...args), {
    stdio: quiet ? "pipe" : "inherit",
    shell: false,
    env,
  });
  return result.status === 0;
}

function killPort(port) {
  if (process.platform === "win32") {
    try {
      const out = execSync(`netstat -ano | findstr ":${port}.*LISTENING"`, {
        encoding: "utf8",
        shell: true,
      });
      for (const line of out.split(/\r?\n/)) {
        const pid = line.trim().split(/\s+/).pop();
        if (!pid || pid === "0") continue;
        spawnSync("taskkill", ["/T", "/F", "/PID", pid], {
          shell: true,
          stdio: "ignore",
        });
        console.error(`Stopped process ${pid} on port ${port}`);
      }
    } catch {
      // nothing listening
    }
    return;
  }
  try {
    execSync(`lsof -ti:${port} | xargs kill -9 2>/dev/null || true`, {
      shell: true,
      stdio: "ignore",
    });
  } catch {
    // nothing listening
  }
}

function killHostDevProcesses() {
  console.error("\n▶ Stopping host dev processes (Next.js :3000, API :8000)…");
  for (const port of HOST_DEV_PORTS) {
    killPort(port);
  }
}

function stopDevComposeStacks(env) {
  console.error("\n▶ Stopping dev Docker stacks…");
  for (const extra of DEV_DOWN_ARGS) {
    for (const obsMode of ["none", "logs", "traces"]) {
      composeDown(["--stack=dev", ...extra], { ...env, AUDIT_DEV_OBS: obsMode });
    }
  }
  for (const extra of DEV_MODULE_ONLY_DOWN_ARGS) {
    for (const obsMode of ["none", "logs", "traces"]) {
      composeDown(["--stack=dev", ...extra], { ...env, AUDIT_DEV_OBS: obsMode });
    }
  }
}

function stopOtherComposeStacks(env, { keepProd = false } = {}) {
  console.error(
    keepProd
      ? "\n▶ Skipping prod / e2e / gpu / vps stacks (--keep-prod)"
      : "\n▶ Stopping prod, e2e, gpu, and vps stacks…"
  );
  if (keepProd) return;

  for (const { stack, args: argSets } of PLATFORM_STACK_DOWN) {
    if (!STACKS[stack]?.files?.length) continue;
    for (const extra of argSets) {
      composeDown([`--stack=${stack}`, ...extra], env);
    }
  }
}

function forceRemoveRepodyContainers() {
  const list = spawnSync(
    "docker",
    ["ps", "-aq", "--filter", "label=com.docker.compose.project=repody"],
    { encoding: "utf8", shell: false }
  );
  const ids = (list.stdout ?? "").trim().split(/\s+/).filter(Boolean);
  if (!ids.length) return;

  console.error(`\n▶ Removing ${ids.length} remaining Repody container(s)…`);
  spawnSync("docker", ["rm", "-f", ...ids], { stdio: "inherit", shell: false });
}

/** @param {string[]} argv */
function runStop(argv) {
  const childEnv = loadRepoEnv({
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
  });

  const keepProd = argv.includes("--keep-prod");
  const wipeVolumes = argv.includes("--volumes");

  killHostDevProcesses();
  stopDevComposeStacks(childEnv);
  stopOtherComposeStacks(childEnv, { keepProd });

  if (wipeVolumes) {
    console.error("\n▶ Removing Repody Docker volumes…");
    for (const extra of [[], ["--warmup"], ["--with=auth"]]) {
      composeDown(
        ["--stack=dev", ...extra, "--volumes"],
        { ...childEnv, AUDIT_DEV_OBS: "none" },
        { quiet: false }
      );
    }
    if (!keepProd) {
      composeDown(["--stack=prod", "--volumes"], childEnv, { quiet: false });
    }
  }

  forceRemoveRepodyContainers();

  console.error("\n✓ Platform fully stopped.\n");
}
