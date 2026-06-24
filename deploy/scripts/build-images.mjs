#!/usr/bin/env node
import { spawn } from "node:child_process";
import { cpSync, mkdirSync, rmSync } from "node:fs";
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
const push = process.argv.includes("--push");
const onlyArg = process.argv.find((arg) => arg.startsWith("--only="));
const only = onlyArg ? onlyArg.slice("--only=".length) : "all";

const image = (name, tag) =>
  registry ? `${registry}/${name}:${tag}` : `${name}:${tag}`;

function stageBenchmarkFixtures() {
  const fixtureRoot = path.join(root, "e2e", "fixtures", "documents");
  const stageDir = path.join(root, "backend", "benchmark-fixtures");
  rmSync(stageDir, { recursive: true, force: true });
  mkdirSync(stageDir, { recursive: true });
  for (const name of ["Facture.pdf", "Facture.benchmark.json"]) {
    cpSync(path.join(fixtureRoot, name), path.join(stageDir, name));
  }
}

function runAsync(cmd, args, env = process.env) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: "inherit",
      cwd: root,
      shell: process.platform === "win32",
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

function want(target) {
  return only === "all" || only === target;
}

/** @param {string[]} args @param {string} cacheName */
function appendBuildKitCacheFlags(args, cacheName) {
  const cacheFrom = process.env.REPODY_BUILDKIT_CACHE_FROM;
  const cacheTo = process.env.REPODY_BUILDKIT_CACHE_TO;
  if (cacheFrom) {
    for (const ref of cacheFrom.split(",")) {
      const trimmed = ref.trim();
      if (trimmed) args.push("--cache-from", trimmed);
    }
  } else {
    const localCache = path.join(root, ".docker-cache", cacheName);
    mkdirSync(localCache, { recursive: true });
    args.push("--cache-from", `type=local,src=${localCache}`);
  }
  if (cacheTo) {
    args.push("--cache-to", cacheTo.trim());
  } else {
    const localCache = path.join(root, ".docker-cache", cacheName);
    mkdirSync(localCache, { recursive: true });
    args.push("--cache-to", `type=local,dest=${localCache},mode=max`);
  }
}

if (want("backend") || want("api") || want("worker")) {
  stageBenchmarkFixtures();
}

if (want("backend") || want("api") || want("worker")) {
  builds.push(
    (async () => {
      const backendImage = image("repody-backend", backendTag);
      const dockerArgs = [
        "build",
        "--target",
        "backend",
        "--build-arg",
        "BACKEND_EXTRAS=otel,ocr",
        "-t",
        backendImage,
        "backend",
      ];
      appendBuildKitCacheFlags(dockerArgs, "backend");
      await runAsync("docker", dockerArgs, buildEnv);
      // Legacy names — same image ID, for registries/tools not yet on repody-backend.
      for (const legacy of ["repody-api", "repody-worker"]) {
        await runAsync("docker", ["tag", backendImage, image(legacy, backendTag)], buildEnv);
      }
    })(),
  );
}

if (want("web") || only === "all") {
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
  `Building Repody images (backend=${backendTag}, web=${webTag}, only=${only}, registry=${registry || "(local)"})`,
);

try {
  await Promise.all(builds);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

if (push) {
  const toPush = [];
  if (want("backend") || want("api") || want("worker") || only === "all") {
    toPush.push(image("repody-backend", backendTag));
    toPush.push(image("repody-api", backendTag));
    toPush.push(image("repody-worker", backendTag));
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
