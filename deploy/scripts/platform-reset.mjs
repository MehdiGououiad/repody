#!/usr/bin/env node
/**
 * Wipe all Repody platform data (Docker volumes + local storage dirs).
 *
 *   pnpm platform:reset           Stop stack, remove volumes, clear local data
 *   pnpm platform:reset -- --up     Same, then start dev stack
 *   pnpm platform:reset -- --up --with=auth
 */
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { buildPlatformSpec } from "../platform-modules.mjs";
import { dockerComposeRootArgs } from "./compose-docker-args.mjs";

const root = process.cwd();
const argv = process.argv.slice(2);
const doUp = argv.includes("--up");
const withArg = argv.find((a) => a.startsWith("--with="));
const withModules = withArg?.slice("--with=".length) ?? "obs,traces,bugsink,auth,edge";

function emptyDir(dir) {
  if (!existsSync(dir)) return;
  for (const name of readdirSync(dir)) {
    rmSync(join(dir, name), { recursive: true, force: true });
  }
}

function rmPath(path) {
  if (existsSync(path)) rmSync(path, { recursive: true, force: true });
}

const spec = buildPlatformSpec({
  stack: "dev",
  withModules: withModules.split(",").map((s) => s.trim()).filter(Boolean),
});

const profiles = [...new Set([...spec.profiles, "web"])];
const profileArgs = profiles.flatMap((p) => ["--profile", p]);

console.error("→ Stopping Repody stack and removing Docker volumes…");
const down = spawnSync(
  "docker",
  [
    "compose",
    ...dockerComposeRootArgs(),
    ...spec.fileArgs,
    ...profileArgs,
    "down",
    "-v",
    "--remove-orphans",
  ],
  { stdio: "inherit", cwd: root, env: process.env }
);
if (down.status !== 0) {
  process.exit(down.status ?? 1);
}

const volList = spawnSync("docker", ["volume", "ls", "-q", "--filter", "name=repody"], {
  encoding: "utf8",
});
const orphanVols = (volList.stdout ?? "")
  .split(/\r?\n/)
  .map((s) => s.trim())
  .filter(Boolean);
if (orphanVols.length) {
  console.error(`→ Removing ${orphanVols.length} leftover repody volume(s)…`);
  spawnSync("docker", ["volume", "rm", "-f", ...orphanVols], { stdio: "inherit" });
}

console.error("→ Clearing local data directories…");
emptyDir(join(root, "benchmark-reports"));
rmPath(join(root, "backend", ".data"));
emptyDir(join(root, "test-results"));
emptyDir(join(root, "playwright-report"));

console.log("Platform data wiped (Postgres, MinIO, Hatchet, Redis, observability, local storage).");

if (doUp) {
  const upArgs = ["compose", "up", "--stack=dev", "--detach"];
  if (withArg) upArgs.push(withArg);
  console.error(`→ pnpm ${upArgs.join(" ")}`);
  const up = spawnSync("pnpm", upArgs, { stdio: "inherit", cwd: root, shell: true });
  process.exit(up.status ?? 0);
}
