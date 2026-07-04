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
const legacyAliases = /^(1|true|yes)$/i.test(
  process.env.REPODY_LEGACY_IMAGE_ALIASES ?? "",
);
const backendExtras = normalizeBackendExtras(
  process.env.REPODY_BACKEND_EXTRAS ?? "otel",
);
const includeBenchmarkFixtures = /^(1|true|yes)$/i.test(
  process.env.REPODY_INCLUDE_BENCHMARK_FIXTURES ?? "",
);
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
  if (value === "api" || value === "worker") {
    return "backend";
  }
  if (["all", "backend", "web", "none"].includes(value)) {
    return value;
  }
  failConfig(
    `Invalid --only=${raw}. Use one of: all, backend, web, none. Legacy api/worker selectors map to backend.`,
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

if ((push || pushOnly) && !registry) {
  failConfig(
    "REPODY_IMAGE_REGISTRY is required for image push. Set it to your Harbor/GHCR path, for example harbor.yourdomain.com/repody.",
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

const builds = [];
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

if (!pushOnly && want("backend")) {
  builds.push(
    (async () => {
      const backendImage = image("repody-backend", backendTag);
      const fixturesContext = benchmarkFixturesContext();
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
      if (legacyAliases) {
        // Compatibility aliases for registries/tools not yet on repody-backend.
        for (const legacy of ["repody-api", "repody-worker"]) {
          await runAsync("docker", ["tag", backendImage, image(legacy, backendTag)], buildEnv);
        }
      }
    })(),
  );
}

if (!pushOnly && (want("web") || only === "all")) {
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
    image("repody-web", webTag),
    ".",
  ];
  appendBuildKitCacheFlags(webArgs, "web");
  builds.push(
    runAsync("docker", webArgs, {
      ...buildEnv,
      AUTH_SECRET: process.env.AUTH_SECRET ?? "build-placeholder-secret-32chars-min",
      AUTH_KEYCLOAK_CLIENT_SECRET:
        process.env.AUTH_KEYCLOAK_CLIENT_SECRET ?? "repody-web-dev-secret",
      AUTH_KEYCLOAK_ISSUER:
        process.env.AUTH_KEYCLOAK_ISSUER ?? "https://auth.example.com/realms/repody",
    }),
  );
}

console.log(
  `${pushOnly ? "Pushing" : "Building"} Repody images (backend=${backendTag}, web=${webTag}, only=${only}, registry=${registry || "(local)"}, backendExtras=${backendExtras}, benchmarkFixtures=${includeBenchmarkFixtures ? "on" : "off"}, legacyAliases=${legacyAliases ? "on" : "off"})`,
);

let buildFailed = false;
try {
  await Promise.all(builds);
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

if (push || pushOnly) {
  const toPush = [];
  if (want("backend") || only === "all") {
    toPush.push(image("repody-backend", backendTag));
    if (legacyAliases) {
      toPush.push(image("repody-api", backendTag));
      toPush.push(image("repody-worker", backendTag));
    }
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
