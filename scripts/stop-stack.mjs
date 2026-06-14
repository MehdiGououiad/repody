#!/usr/bin/env node
/**
 * Stop local Next.js (port 3000) and the dev Docker stack.
 * Usage: pnpm dev:stop
 */
import { spawnSync } from "node:child_process";
import { execSync } from "node:child_process";

const childEnv = {
  ...process.env,
  DOCKER_BUILDKIT: "1",
  COMPOSE_DOCKER_CLI_BUILD: "1",
};

function killPort(port) {
  if (process.platform === "win32") {
    try {
      const out = execSync(`netstat -ano | findstr ":${port}.*LISTENING"`, {
        encoding: "utf8",
        shell: true,
      });
      const pids = new Set(
        out
          .split(/\r?\n/)
          .map((line) => line.trim().split(/\s+/).pop())
          .filter((pid) => pid && pid !== "0")
      );
      for (const pid of pids) {
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

console.error("\n▶ Stopping frontend on :3000…");
killPort(3000);

console.error("\n▶ Stopping Docker stack…\n");
for (const cmd of ["down:warmup", "down"]) {
  const result = spawnSync("node", ["scripts/docker.mjs", cmd], {
    stdio: "inherit",
    shell: process.platform === "win32",
    env: { ...childEnv, AUDIT_DEV_OBS: "traces" },
  });
  if (result.status === 0) break;
}

console.error("\n✓ Platform stopped.\n");
