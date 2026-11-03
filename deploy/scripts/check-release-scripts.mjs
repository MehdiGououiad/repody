#!/usr/bin/env node
/** Contract checks for docker-bake.hcl via `docker buildx bake --print` (no build). */
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

function bakeEnv(overrides = {}) {
  const env = { ...process.env };
  for (const key of Object.keys(env)) {
    if (key.startsWith("REPODY_")) delete env[key];
  }
  return { ...env, ...overrides };
}

function bakePrint(env, targets = []) {
  const result = spawnSync(
    "docker",
    ["buildx", "bake", "-f", "docker-bake.hcl", "--print", ...targets],
    { cwd: root, env: bakeEnv(env), encoding: "utf8" }
  );
  let config = null;
  try {
    config = JSON.parse(result.stdout);
  } catch {
    // validation failures print no JSON
  }
  return { status: result.status, output: `${result.stdout ?? ""}${result.stderr ?? ""}`, config };
}

const checks = [
  {
    name: "defaults resolve to local dev tags",
    env: {},
    expect: (c) =>
      c.target.backend.tags[0] === "repody-backend:dev" &&
      c.target.web.tags[0] === "repody-web:dev" &&
      c.target.backend.args.BACKEND_EXTRAS === "otel" &&
      !c.target.backend.contexts &&
      !c.target.backend.platforms,
  },
  {
    name: "registry, per-image tags and platforms",
    env: {
      REPODY_IMAGE_REGISTRY: "example.invalid/repody",
      REPODY_IMAGE_TAG: "0.1.0",
      REPODY_WEB_IMAGE_TAG: "0.1.1",
      REPODY_IMAGE_PLATFORMS: "linux/amd64,linux/arm64",
    },
    expect: (c) =>
      c.target.backend.tags[0] === "example.invalid/repody/repody-backend:0.1.0" &&
      c.target.web.tags[0] === "example.invalid/repody/repody-web:0.1.1" &&
      c.target.web.platforms?.join(",") === "linux/amd64,linux/arm64",
  },
  {
    name: "benchmark fixtures add the named context",
    env: { REPODY_INCLUDE_BENCHMARK_FIXTURES: "true" },
    expect: (c) =>
      c.target.backend.contexts?.["benchmark-fixtures"] === "e2e/fixtures/documents" &&
      c.target.backend.args.INCLUDE_BENCHMARK_FIXTURES === "true",
  },
  { name: "reject mutable latest tag", env: { REPODY_IMAGE_TAG: "latest" }, fail: "immutable tag" },
  {
    name: "reject invalid backend extra",
    env: { REPODY_BACKEND_EXTRAS: "otel,../bad" },
    fail: "comma-separated Python extra names",
  },
];

const failures = [];
for (const check of checks) {
  const { status, output, config } = bakePrint(check.env);
  const ok = check.fail
    ? status !== 0 && output.includes(check.fail)
    : status === 0 && config && check.expect(config);
  if (!ok) failures.push(`${check.name}: status ${status}\n${output.trim()}`);
}

if (failures.length) {
  console.error(failures.join("\n\n"));
  process.exit(1);
}
console.log("ok: docker-bake.hcl release contract");
