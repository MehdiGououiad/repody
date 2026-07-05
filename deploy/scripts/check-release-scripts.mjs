#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const baseEnv = {
  ...releaseNeutralEnv(),
  REPODY_BUILDKIT_LOCAL_CACHE_DIR: resolve(root, ".tmp", "check-release-buildkit-cache"),
};

function releaseNeutralEnv() {
  const env = { ...process.env };
  for (const key of [
    "REGISTRY",
    "TAG",
    "REPODY_BACKEND_EXTRAS",
    "REPODY_BACKEND_IMAGE_TAG",
    "REPODY_BUILDKIT_CACHE_FROM",
    "REPODY_BUILDKIT_CACHE_TO",
    "REPODY_BUILDKIT_BACKEND_CACHE_FROM",
    "REPODY_BUILDKIT_BACKEND_CACHE_TO",
    "REPODY_BUILDKIT_WEB_CACHE_FROM",
    "REPODY_BUILDKIT_WEB_CACHE_TO",
    "REPODY_IMAGE_REGISTRY",
    "REPODY_IMAGE_TAG",
    "REPODY_INCLUDE_BENCHMARK_FIXTURES",
    "REPODY_WEB_IMAGE_TAG",
  ]) {
    delete env[key];
  }
  return env;
}

const checks = [
  {
    name: "images build no-op selector",
    args: ["deploy/scripts/build-images.mjs", "--only=none"],
    ok: true,
  },
  {
    name: "images build no-op selector separated",
    args: ["deploy/scripts/build-images.mjs", "--only", "none"],
    ok: true,
  },
  {
    name: "images push-only no-op with registry",
    args: ["deploy/scripts/build-images.mjs", "--push-only", "--only=none"],
    env: { REPODY_IMAGE_REGISTRY: "example.invalid/repody" },
    ok: true,
  },
  {
    name: "images reject unknown option",
    args: ["deploy/scripts/build-images.mjs", "--wat"],
    ok: false,
    stderr: "Unknown option: --wat",
  },
  {
    name: "images reject missing only value",
    args: ["deploy/scripts/build-images.mjs", "--only"],
    ok: false,
    stderr: "Missing value for --only",
  },
  {
    name: "images reject push conflict",
    args: ["deploy/scripts/build-images.mjs", "--push", "--push-only", "--only=none"],
    env: { REPODY_IMAGE_REGISTRY: "example.invalid/repody" },
    ok: false,
    stderr: "Use either --push or --push-only",
  },
  {
    name: "images reject push without registry",
    args: ["deploy/scripts/build-images.mjs", "--push-only", "--only=none"],
    ok: false,
    stderr: "REPODY_IMAGE_REGISTRY is required",
  },
  {
    name: "images reject invalid backend extra",
    args: ["deploy/scripts/build-images.mjs", "--only=none"],
    env: { REPODY_BACKEND_EXTRAS: "otel,../bad" },
    ok: false,
    stderr: "Invalid REPODY_BACKEND_EXTRAS entry",
  },
  {
    name: "openshift client test reject unknown command",
    args: ["deploy/scripts/openshift-client-test.mjs", "nope"],
    ok: false,
    stderr: "Unknown command",
  },
];

const failures = [];

for (const check of checks) {
  const result = spawnSync("node", check.args, {
    cwd: root,
    env: { ...baseEnv, ...(check.env ?? {}) },
    encoding: "utf8",
  });
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  const passedStatus = check.ok ? result.status === 0 : result.status !== 0;
  const passedText = check.stderr ? output.includes(check.stderr) : true;
  if (!passedStatus || !passedText) {
    failures.push(
      `${check.name}: expected ${check.ok ? "success" : "failure"}${
        check.stderr ? ` containing "${check.stderr}"` : ""
      }, got status ${result.status}\n${output.trim()}`,
    );
  }
}

if (failures.length) {
  console.error(failures.join("\n\n"));
  process.exit(1);
}

console.log("ok: release script CLI contracts");
