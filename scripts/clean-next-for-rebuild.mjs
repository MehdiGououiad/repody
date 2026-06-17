#!/usr/bin/env node
/**
 * Prepare a clean `next build` on Windows / OneDrive:
 * - stop a leftover standalone web server that locks `.next`
 * - remove `.next` (retries EPERM from sync or open handles)
 */
import { existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const nextDir = join(process.cwd(), ".next");

function stopStaleStandaloneWeb() {
  if (process.platform === "win32") {
    spawnSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process -Filter \"name='node.exe'\" " +
          "| Where-Object { $_.CommandLine -match 'standalone[\\\\/]server\\.js' } " +
          "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
      ],
      { stdio: "ignore", shell: false }
    );
    return;
  }

  spawnSync("pkill", ["-f", ".next/standalone/server"], { stdio: "ignore" });
}

function removeNextOutput() {
  if (!existsSync(nextDir)) return;

  rmSync(nextDir, {
    recursive: true,
    force: true,
    maxRetries: 8,
    retryDelay: 400,
  });
}

stopStaleStandaloneWeb();
removeNextOutput();
console.error("✓ Cleaned .next for rebuild");
