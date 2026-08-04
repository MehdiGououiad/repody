#!/usr/bin/env node
import { spawn } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const registry = (process.env.REPODY_IMAGE_REGISTRY ?? process.env.REGISTRY ?? "")
  .replace(/\/$/, "");
const backendTag =
  process.env.REPODY_BACKEND_IMAGE_TAG ??
  process.env.REPODY_IMAGE_TAG ??
  process.env.TAG ??
  "latest";
const webTag =
  process.env.REPODY_WEB_IMAGE_TAG ??
  process.env.REPODY_IMAGE_TAG ??
  process.env.TAG ??
  backendTag;
const { push, pushOnly, only } = parseArgs(process.argv);
const backendExtras = normalizeBackendExtras(
  process.env.REPODY_BACKEND_EXTRAS ?? "otel,glmocr",
);
const includeBenchmarkFixtures = /^(1|true|yes)$/i.test(
  process.env.REPODY_INCLUDE_BENCHMARK_FIXTURES ?? "",
);
const platforms = normalizePlatforms(process.env.REPODY_IMAGE_PLATFORMS ?? "");
const multiPlatform = platforms.length > 0;
const localCacheRoot =
  process.env.REPODY_BUILDKIT_LOCAL_CACHE_DIR ??
  (process.platform === "win32" && root.toLowerCase().includes(`${path.sep}onedrive${path.sep}`)
    ? path.join(os.homedir(), ".cache", "repody", "docker-buildkit")
    : path.join(root, ".docker-cache"));

const image = (name, tag) =>
  registry ? `${registry}/${name}:${tag}` : `${name}:${tag}`;

function failConfig(message) {
  console.error(message);
  process.exit(1);
}

function parseArgs(argv) {
  let push = false;
  let pushOnly = false;
  let only = "all";
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--push") {
      push = true;
    } else if (arg === "--push-only") {
      pushOnly = true;
    } else if (arg === "--only") {
      const value = argv[++i] ?? "";
      if (!value || value.startsWith("--")) {
        failConfig("Missing value for --only. Use one of: all, backend, web, none.");
      }
      only = normalizeOnly(value);
    } else if (arg.startsWith("--only=")) {
      only = normalizeOnly(arg.slice("--only=".length));
    } else {
      failConfig(`Unknown option: ${arg}`);
    }
  }
  if (push && pushOnly) {
    failConfig("Use either --push or --push-only, not both.");
  }
  return { push, pushOnly, only };
}

function normalizeOnly(raw) {
  const value = raw.trim().toLowerCase();
  if (["all", "backend", "web", "none"].includes(value)) {
    return value;
  }
  failConfig(
    `Invalid --only=${raw}. Use one of: all, backend, web, none.`,
  );
}

function normalizeBackendExtras(raw) {
  const extras = raw
    .split(/[,\s]+/)
    .map((extra) => extra.trim())
    .filter(Boolean);
  for (const extra of extras) {
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(extra)) {
      failConfig(
        `Invalid REPODY_BACKEND_EXTRAS entry "${extra}". Use comma-separated Python extra names, for example "otel".`,
      );
    }
  }
  return extras.length ? extras.join(",") : "otel";
}

function normalizePlatforms(raw) {
  return raw
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}

if ((push || pushOnly) && !registry) {
  failConfig(
    "REPODY_IMAGE_REGISTRY is required for image push. Set it to your Docker Hub namespace, GHCR path, or client registry, for example mehdigououiad or ghcr.io/yourorg/repody.",
  );
}

if (multiPlatform && pushOnly) {
  failConfig(
    "REPODY_IMAGE_PLATFORMS cannot be used with --push-only. Multi-arch images must be built with buildx --push in one step.",
  );
}

if (multiPlatform && !push) {
  failConfig(
    "REPODY_IMAGE_PLATFORMS requires --push (or pnpm images:release). Multi-arch manifests cannot be loaded into a single local Docker daemon.",
  );
}

function runAsync(cmd, args, env = process.env) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: "inherit",
      cwd: root,
      shell: false,
      env,
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} ${args.join(" ")} exited ${code}`));
    });
  });
}

const buildEnv = {
  ...process.env,
  DOCKER_BUILDKIT: "1",
};

/** @type {Array<() => Promise<void>>} */
const buildJobs = [];
const cleanupDirs = [];

function want(target) {
  return only === "all" || only === target;
}

function benchmarkFixturesContext() {
  const dir = mkdtempSync(path.join(os.tmpdir(), "repody-benchmark-fixtures-"));
  cleanupDirs.push(dir);
  if (includeBenchmarkFixtures) {
    const fixtureRoot = path.join(root, "e2e", "fixtures", "documents");
    for (const name of ["Facture.pdf", "Facture.benchmark.json"]) {
      cpSync(path.join(fixtureRoot, name), path.join(dir, name));
    }
    return dir;
  }
  writeFileSync(path.join(dir, ".keep"), "", "utf8");
  return dir;
}

/** @param {string[]} args @param {string} cacheName */
function appendBuildKitCacheFlags(args, cacheName) {
  const envPrefix = `REPODY_BUILDKIT_${cacheName.toUpperCase().replace(/[^A-Z0-9]/g, "_")}`;
  const cacheFrom =
    process.env[`${envPrefix}_CACHE_FROM`] ?? process.env.REPODY_BUILDKIT_CACHE_FROM;
  const cacheTo =
    process.env[`${envPrefix}_CACHE_TO`] ?? process.env.REPODY_BUILDKIT_CACHE_TO;
  if (cacheFrom) {
    for (const ref of cacheFrom.split(",")) {
      const trimmed = ref.trim();
      if (trimmed) args.push("--cache-from", trimmed);
    }
  } else {
    const localCache = path.join(localCacheRoot, cacheName);
    mkdirSync(localCache, { recursive: true });
    args.push("--cache-from", `type=local,src=${localCache}`);
  }
  if (cacheTo) {
    args.push("--cache-to", cacheTo.trim());
  } else {
    const localCache = path.join(localCacheRoot, cacheName);
    mkdirSync(localCache, { recursive: true });
    args.push("--cache-to", `type=local,dest=${localCache},mode=max`);
  }
}

async function ensureBuildxBuilder() {
  if (!multiPlatform) return;
  const name = process.env.REPODY_BUILDX_BUILDER || "repody-multiarch";
  const listed = await new Promise((resolve) => {
    const child = spawn("docker", ["buildx", "inspect", name], {
      stdio: "ignore",
      cwd: root,
      shell: false,
    });
    child.on("close", (code) => resolve(code === 0));
  });
  if (!listed) {
    await runAsync(
      "docker",
      ["buildx", "create", "--name", name, "--driver", "docker-container", "--use"],
      buildEnv,
    );
  } else {
    await runAsync("docker", ["buildx", "use", name], buildEnv);
  }
  await runAsync("docker", ["buildx", "inspect", "--bootstrap"], buildEnv);
}

if (!pushOnly && want("backend")) {
  buildJobs.push(async () => {
    const backendImage = image("repody-backend", backendTag);
    const fixturesContext = benchmarkFixturesContext();
    if (multiPlatform) {
      const dockerArgs = [
        "buildx",
        "build",
        "--platform",
        platforms.join(","),
        "--target",
        "backend",
        "--build-context",
        `benchmark-fixtures=${fixturesContext}`,
        "--build-arg",
        `BACKEND_EXTRAS=${backendExtras}`,
        "--build-arg",
        `INCLUDE_BENCHMARK_FIXTURES=${includeBenchmarkFixtures ? "true" : "false"}`,
        "-t",
        backendImage,
        "--push",
        "backend",
      ];
      appendBuildKitCacheFlags(dockerArgs, "backend");
      await runAsync("docker", dockerArgs, buildEnv);
      return;
    }
    const dockerArgs = [
      "build",
      "--target",
      "backend",
      "--build-context",
      `benchmark-fixtures=${fixturesContext}`,
      "--build-arg",
      `BACKEND_EXTRAS=${backendExtras}`,
      "--build-arg",
      `INCLUDE_BENCHMARK_FIXTURES=${includeBenchmarkFixtures ? "true" : "false"}`,
      "-t",
      backendImage,
      "backend",
    ];
    appendBuildKitCacheFlags(dockerArgs, "backend");
    await runAsync("docker", dockerArgs, buildEnv);
  });
}

if (!pushOnly && (want("web") || only === "all")) {
  buildJobs.push(async () => {
    const webImage = image("repody-web", webTag);
    const webEnv = {
      ...buildEnv,
      AUTH_SECRET: process.env.AUTH_SECRET ?? "build-placeholder-secret-32chars-min",
      AUTH_KEYCLOAK_CLIENT_SECRET:
        process.env.AUTH_KEYCLOAK_CLIENT_SECRET ?? "repody-web-dev-secret",
      AUTH_KEYCLOAK_ISSUER:
        process.env.AUTH_KEYCLOAK_ISSUER ?? "https://auth.example.com/realms/repody",
    };
    if (multiPlatform) {
      const webArgs = [
        "buildx",
        "build",
        "--platform",
        platforms.join(","),
        "-f",
        "Dockerfile.web",
        "--build-arg",
        `BACKEND_URL=${process.env.REPODY_WEB_BACKEND_URL ?? "http://repody-api:8000"}`,
        "--build-arg",
        `NEXT_PUBLIC_BUGSINK_DSN=${process.env.NEXT_PUBLIC_BUGSINK_DSN ?? ""}`,
        "--build-arg",
        `BUGSINK_DSN=${process.env.BUGSINK_DSN ?? ""}`,
        "-t",
        webImage,
        "--push",
        ".",
      ];
      appendBuildKitCacheFlags(webArgs, "web");
      await runAsync("docker", webArgs, webEnv);
      return;
    }
    const webArgs = [
      "build",
      "-f",
      "Dockerfile.web",
      "--build-arg",
      `BACKEND_URL=${process.env.REPODY_WEB_BACKEND_URL ?? "http://repody-api:8000"}`,
      "--build-arg",
      `NEXT_PUBLIC_BUGSINK_DSN=${process.env.NEXT_PUBLIC_BUGSINK_DSN ?? ""}`,
      "--build-arg",
      `BUGSINK_DSN=${process.env.BUGSINK_DSN ?? ""}`,
      "-t",
      webImage,
      ".",
    ];
    appendBuildKitCacheFlags(webArgs, "web");
    await runAsync("docker", webArgs, webEnv);
  });
}

console.log(
  `${pushOnly ? "Pushing" : "Building"} Repody images (backend=${backendTag}, web=${webTag}, only=${only}, registry=${registry || "(local)"}, backendExtras=${backendExtras}, platforms=${platforms.join(",") || "host"}, benchmarkFixtures=${includeBenchmarkFixtures ? "on" : "off"})`,
);

let buildFailed = false;
try {
  await ensureBuildxBuilder();
  // Multi-arch QEMU builds are heavy; run sequentially to avoid builder contention.
  if (multiPlatform) {
    for (const job of buildJobs) {
      await job();
    }
  } else {
    await Promise.all(buildJobs.map((job) => job()));
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  buildFailed = true;
} finally {
  for (const dir of cleanupDirs) {
    rmSync(dir, { recursive: true, force: true });
  }
}
if (buildFailed) {
  process.exit(1);
}

if ((push || pushOnly) && !multiPlatform) {
  const toPush = [];
  if (want("backend") || only === "all") {
    toPush.push(image("repody-backend", backendTag));
  }
  if (want("web") || only === "all") {
    toPush.push(image("repody-web", webTag));
  }
  for (const name of [...new Set(toPush)]) {
    console.log(`\nPushing ${name}`);
    await runAsync("docker", ["push", name], buildEnv);
  }
}

console.log("\nDone.");
