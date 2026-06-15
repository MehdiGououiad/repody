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

function runSync(label, command, args, env = process.env) {
  console.error(`\n▶ ${label}\n`);
  const result = spawnSync(command, args, {
    stdio: "inherit",
    shell: process.platform === "win32",
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
  const overlayArgs = warmup ? ["--warmup"] : [];
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

  const bugsinkModuleArgs =
    childEnv.BUGSINK_DSN || childEnv.NEXT_PUBLIC_BUGSINK_DSN
      ? ["--with=bugsink"]
      : [];

  const needsBugsinkRebuild =
    Boolean(childEnv.NEXT_PUBLIC_BUGSINK_DSN) && envFileIsNewerThanBuild();

  function stopDocker() {
    if (!stackStarted) return;
    console.error("\n▶ Stopping Docker stack…\n");
    spawnSync("node", composeArgs("down", "--stack=dev", ...overlayArgs), {
      stdio: "inherit",
      shell: process.platform === "win32",
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
    [...composeArgs("up", "--stack=dev", ...overlayArgs, ...bugsinkModuleArgs, "--only=infra")],
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
      ? "Starting backend with Repody VLM warmup enabled"
      : "Starting backend without warmup (fast boot)",
    "node",
    [...composeArgs("up", "--stack=dev", ...overlayArgs, ...bugsinkModuleArgs, "--only=services")],
    childEnv
  );

  runSync("Waiting for API health", "node", ["scripts/wait-for-api.mjs"], childEnv);

  if (warmup) {
    runSync(
      "Waiting for Repody VLM warmup",
      "node",
      ["scripts/wait-for-warmup.mjs"],
      { ...childEnv, AUDIT_COMPOSE_WARMUP: "1" }
    );
  }

  if (forceRebuild || needsBugsinkRebuild || !existsSync(buildIdPath)) {
    if (needsBugsinkRebuild && !forceRebuild) {
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
  printPlatformBanner({
    mode: "dev",
    logs: withLogs,
    traces: withTraces,
    footer: [
      "Docker logs: api, worker, worker-fast, postgres, redis, minio, hatchet",
      obsLines,
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
    composeArgs("logs", "--stack=dev", ...overlayArgs, ...bugsinkModuleArgs),
    {
      stdio: "inherit",
      shell: process.platform === "win32",
      env: childEnv,
      cwd: process.cwd(),
    }
  );

  logsProcess.on("exit", () => {
    logsProcess = null;
    if (!shuttingDown) shutdown("docker logs exited");
  });

  webProcess = spawnPrefixed("web", process.execPath, [standaloneServerPath], {
    env: { ...childEnv, PORT: childEnv.PORT ?? "3000" },
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
      "Waiting for Repody VLM warmup",
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
      footer: "Streaming logs · Ctrl+C ends log stream · pnpm stop -- --prod to tear down",
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
      footer: "Detached mode — containers keep running · pnpm stop -- --prod to tear down",
    });
  }
}

function runProdDown() {
  runSync("Stopping production stack", "node", [
    ...composeArgs("down", "--stack=prod", "--warmup"),
  ]);
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

/** @param {string[]} argv */
function runStop(argv) {
  const childEnv = {
    ...process.env,
    DOCKER_BUILDKIT: "1",
    COMPOSE_DOCKER_CLI_BUILD: "1",
  };

  console.error("\n▶ Stopping frontend on :3000…");
  killPort(3000);

  console.error("\n▶ Stopping dev Docker stack…\n");
  for (const warmup of [false, true]) {
    const overlayArgs = warmup ? ["--warmup"] : [];
    for (const obsMode of ["none", "logs", "traces"]) {
      spawnSync("node", composeArgs("down", "--stack=dev", ...overlayArgs), {
        stdio: "inherit",
        shell: process.platform === "win32",
        env: { ...childEnv, AUDIT_DEV_OBS: obsMode },
      });
    }
  }

  if (argv.includes("--prod")) {
    runProdDown();
  }

  console.error("\n✓ Platform stopped.\n");
}
