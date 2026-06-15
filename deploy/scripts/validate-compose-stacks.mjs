#!/usr/bin/env node
/**
 * Validate compose stack presets and common overlay combinations.
 */
import { spawnSync } from "node:child_process";
import { buildPlatformSpec } from "../platform-modules.mjs";
import { dockerComposeRootArgs } from "./compose-docker-args.mjs";

/** @type {Array<{ label: string, options: Parameters<typeof buildPlatformSpec>[0] }>} */
const VARIANTS = [
  { label: "dev", options: { stack: "dev" } },
  { label: "dev+warmup", options: { stack: "dev", overlays: { warmup: true } } },
  { label: "prod", options: { stack: "prod" } },
  { label: "prod+warmup", options: { stack: "prod", overlays: { warmup: true } } },
  { label: "prod+lan", options: { stack: "prod", overlays: { lan: true } } },
  { label: "prod+public", options: { stack: "prod", overlays: { public: true } } },
  { label: "prod+scale", options: { stack: "prod", overlays: { scale: true } } },
  { label: "prod-micro", options: { stack: "prod-micro" } },
  { label: "vps", options: { stack: "vps" } },
  { label: "vps+obs", options: { stack: "vps", withModules: ["obs", "traces"] } },
  { label: "gpu", options: { stack: "gpu" } },
  { label: "e2e", options: { stack: "e2e" } },
  { label: "dev+bugsink", options: { stack: "dev", withModules: ["bugsink"] } },
  { label: "modules-only+bugsink", options: { stack: "dev", modulesOnly: true, withModules: ["bugsink"] } },
];

const ENV = {
  ...process.env,
  AUDIT_ADMIN_API_TOKEN: process.env.AUDIT_ADMIN_API_TOKEN ?? "ci-test-token",
  AUDIT_MINIO_PUBLIC_ENDPOINT:
    process.env.AUDIT_MINIO_PUBLIC_ENDPOINT ?? "files.example.com",
  POSTGRES_PASSWORD: process.env.POSTGRES_PASSWORD ?? "ci-postgres",
  MINIO_ROOT_PASSWORD: process.env.MINIO_ROOT_PASSWORD ?? "ci-minio",
  PUBLIC_HOST: process.env.PUBLIC_HOST ?? "app.example.com",
  PUBLIC_DOMAIN: process.env.PUBLIC_DOMAIN ?? "app.example.com",
  FILES_DOMAIN: process.env.FILES_DOMAIN ?? "files.example.com",
  BASIC_AUTH_USER: process.env.BASIC_AUTH_USER ?? "repody",
  BASIC_AUTH_HASH: process.env.BASIC_AUTH_HASH ?? "ci-placeholder-hash",
  BUGSINK_SECRET_KEY:
    process.env.BUGSINK_SECRET_KEY ??
    "ci-bugsink-secret-key-at-least-fifty-characters-long",
  BUGSINK_DB_PASSWORD: process.env.BUGSINK_DB_PASSWORD ?? "ci-bugsink-db",
};

let failed = false;

for (const { label, options } of VARIANTS) {
  const spec = buildPlatformSpec(options);
  const args = [
    "compose",
    ...dockerComposeRootArgs(),
    ...spec.fileArgs,
    ...spec.profiles.flatMap((p) => ["--profile", p]),
    "config",
    "--quiet",
  ];

  const result = spawnSync("docker", args, { encoding: "utf-8", env: ENV });

  if (result.status !== 0) {
    failed = true;
    console.error(`\n✗ ${label} failed:\n${result.stderr || result.stdout}`);
  } else {
    console.error(`✓ ${label}`);
  }
}

if (failed) process.exit(1);
console.error("\nAll compose variants validate OK.");
