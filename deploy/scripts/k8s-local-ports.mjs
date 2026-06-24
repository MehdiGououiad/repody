import { execSync } from "node:child_process";
import { spawnSync } from "node:child_process";

/** Host ports reserved for the local Gateway (kind extraPortMappings). */
const GATEWAY_PORTS = [80, 443];

function shouldSkipPid(pid) {
  if (process.platform !== "win32") return false;
  try {
    const proc = execSync(`tasklist /FI "PID eq ${pid}" /FO CSV /NH`, {
      encoding: "utf8",
      shell: true,
    });
    return /docker|com\.docker|vpnkit|wslrelay/i.test(proc);
  } catch {
    return false;
  }
}

export function killPort(port) {
  if (process.platform === "win32") {
    try {
      const out = execSync(`netstat -ano | findstr ":${port}.*LISTENING"`, {
        encoding: "utf8",
        shell: true,
      });
      for (const line of out.split(/\r?\n/)) {
        const pid = line.trim().split(/\s+/).pop();
        if (!pid || pid === "0") continue;
        if (shouldSkipPid(pid)) {
          console.error(`Skipping Docker-related process ${pid} on port ${port}`);
          continue;
        }
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

export function ensureGatewayPortsFree() {
  console.error("\n> Freeing host ports 80/443 for Gateway ingress\n");
  for (const port of GATEWAY_PORTS) {
    killPort(port);
  }
}
