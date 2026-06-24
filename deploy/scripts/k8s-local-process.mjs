import { spawnSync } from "node:child_process";

let traceStartMs = Date.now();
let tracePhaseStartMs = Date.now();
/** @type {{ label: string, phaseSec: number, totalSec: number }[]} */
const tracePhases = [];
/** @type {{ cmd: string, sec: number }[]} */
const traceCommands = [];

export function traceEnabled() {
  return hasFlag("--trace") || truthyEnv("REPODY_K8S_LOCAL_TRACE");
}

/** @param {string} label */
export function traceNote(label) {
  if (!traceEnabled()) return;
  const now = Date.now();
  const totalSec = (now - traceStartMs) / 1000;
  const phaseSec = (now - tracePhaseStartMs) / 1000;
  tracePhases.push({ label, phaseSec, totalSec });
  console.error(
    `[trace +${totalSec.toFixed(1)}s | phase ${phaseSec.toFixed(1)}s] ${label}`,
  );
  tracePhaseStartMs = now;
}

/** @param {string} cmd @param {string[]} args @param {number} durationMs */
function traceCommand(cmd, args, durationMs) {
  if (!traceEnabled()) return;
  const preview = [cmd, ...args.slice(0, 5)].join(" ");
  const suffix = args.length > 5 ? " …" : "";
  const sec = durationMs / 1000;
  traceCommands.push({ cmd: `${preview}${suffix}`, sec });
  if (sec >= 1) {
    console.error(`[trace cmd ${sec.toFixed(1)}s] ${preview}${suffix}`);
  }
}

export function traceSummary() {
  if (!traceEnabled()) return;
  const totalSec = (Date.now() - traceStartMs) / 1000;
  console.error("\n══════════════════════════════════════════════════════════════════════");
  console.error(` TRACE SUMMARY — total ${totalSec.toFixed(1)}s`);
  console.error("──────────────────────────────────────────────────────────────────────");
  const sorted = [...tracePhases].toSorted((a, b) => b.phaseSec - a.phaseSec);
  for (const row of sorted.slice(0, 12)) {
    console.error(`  ${row.phaseSec.toFixed(1).padStart(7)}s  ${row.label}`);
  }
  const slowCmds = [...traceCommands].toSorted((a, b) => b.sec - a.sec).slice(0, 8);
  if (slowCmds.length) {
    console.error("──────────────────────────────────────────────────────────────────────");
    console.error(" Slowest subprocesses:");
    for (const row of slowCmds) {
      console.error(`  ${row.sec.toFixed(1).padStart(7)}s  ${row.cmd}`);
    }
  }
  console.error("══════════════════════════════════════════════════════════════════════\n");
}

/** @param {string} cwd */
export function createProcessAdapter(cwd) {
  /** @param {string} cmd @param {string[]} args @param {Record<string, string | undefined>} [extraEnv] */
  function run(cmd, args, extraEnv = {}) {
    const started = Date.now();
    const result = spawnSync(cmd, args, {
      stdio: "inherit",
      cwd,
      env: { ...process.env, ...extraEnv },
      shell: process.platform === "win32",
    });
    traceCommand(cmd, args, Date.now() - started);
    if (result.status !== 0) {
      traceSummary();
      process.exit(result.status ?? 1);
    }
  }

  /** @param {string} cmd @param {string[]} args */
  function capture(cmd, args) {
    const result = spawnSync(cmd, args, {
      encoding: "utf8",
      cwd,
      shell: process.platform === "win32",
    });
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || `${cmd} failed`);
    }
    return (result.stdout ?? "").trim();
  }

  /** @param {string} cmd @param {string[]} args */
  function captureNoShell(cmd, args) {
    const result = spawnSync(cmd, args, {
      encoding: "utf8",
      cwd,
      shell: false,
    });
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || `${cmd} failed`);
    }
    return (result.stdout ?? "").trim();
  }

  /** @param {string} cmd @param {string[]} args @param {Record<string, string | undefined>} [extraEnv] */
  function runNoShell(cmd, args, extraEnv = {}) {
    const result = spawnSync(cmd, args, {
      stdio: "inherit",
      cwd,
      env: { ...process.env, ...extraEnv },
      shell: false,
    });
    if (result.status !== 0) {
      process.exit(result.status ?? 1);
    }
  }

  /** @param {string} cmd @param {string[]} args @param {string} input */
  function captureWithInput(cmd, args, input) {
    const result = spawnSync(cmd, args, {
      input,
      encoding: "utf8",
      cwd,
      shell: process.platform === "win32",
    });
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || `${cmd} failed`);
    }
    return (result.stdout ?? "").trim();
  }

  /** @param {unknown} manifest */
  function applyJson(manifest) {
    const result = spawnSync("kubectl", ["apply", "-f", "-"], {
      input: JSON.stringify(manifest),
      encoding: "utf8",
      cwd,
      stdio: ["pipe", "inherit", "inherit"],
      shell: process.platform === "win32",
    });
    if (result.status !== 0) {
      process.exit(result.status ?? 1);
    }
  }

  function captureOptional(cmd, args) {
    try {
      return capture(cmd, args);
    } catch (error) {
      return String(error?.message || error);
    }
  }

  function captureOptionalNoShell(cmd, args) {
    try {
      return captureNoShell(cmd, args);
    } catch (error) {
      return String(error?.message || error);
    }
  }

  return {
    applyJson,
    capture,
    captureNoShell,
    captureOptional,
    captureOptionalNoShell,
    captureWithInput,
    run,
    runNoShell,
  };
}

export function heading(text) {
  traceNote(text);
  console.error(`\n> ${text}\n`);
}

export function hasFlag(name) {
  return process.argv.includes(name);
}

export function truthyEnv(name) {
  return ["1", "true", "yes"].includes(String(process.env[name] || "").toLowerCase());
}

/** Exit unless the Docker engine accepts commands (not just the CLI shim). */
export function requireDockerEngine() {
  const result = spawnSync("docker", ["ps", "-q"], {
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  if (result.status === 0) {
    return;
  }
  const detail = (result.stderr || result.stdout || "").trim();
  console.error("\n✗ Docker engine is not running.");
  console.error(
    "  Start Docker Desktop, wait until the engine is ready, then retry:\n",
  );
  console.error("  pnpm k8s:local:reset\n");
  if (detail) {
    console.error(`  ${detail.split(/\r?\n/)[0]}\n`);
  }
  process.exit(result.status ?? 1);
}

export function sleep(ms) {
  if (process.platform === "win32") {
    spawnSync("powershell", ["-Command", `Start-Sleep -Milliseconds ${ms}`], {
      stdio: "ignore",
    });
  } else {
    spawnSync("sleep", [String(Math.ceil(ms / 1000))], { stdio: "ignore" });
  }
}

export function waitFor(condition, label, timeoutMs = 600_000, intervalMs = 5_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (condition()) {
      console.error(`ok: ${label}`);
      return;
    }
    console.error(`waiting for ${label}`);
    sleep(intervalMs);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

export function waitForWithProgress(
  condition,
  label,
  timeoutMs = 600_000,
  intervalMs = 5_000,
  progress = () => {},
  progressEveryMs = 30_000,
) {
  const start = Date.now();
  let lastProgress = 0;
  while (Date.now() - start < timeoutMs) {
    if (condition()) {
      console.error(`ok: ${label}`);
      return;
    }
    const elapsed = Date.now() - start;
    const remaining = Math.max(0, timeoutMs - elapsed);
    console.error(
      `waiting for ${label} (${Math.ceil(elapsed / 1000)}s elapsed, ${Math.ceil(remaining / 1000)}s left)`,
    );
    if (elapsed - lastProgress >= progressEveryMs) {
      lastProgress = elapsed;
      progress();
    }
    sleep(intervalMs);
  }
  progress();
  throw new Error(`Timed out waiting for ${label}`);
}
