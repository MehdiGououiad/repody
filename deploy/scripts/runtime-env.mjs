import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const BACKEND_ENV = path.join(ROOT, "backend/.env");

/** Absolute path of `name` on PATH (Windows prefers the `.exe` hit), or null. */
export function findExecutable(name) {
  const isWin = process.platform === "win32";
  const result = spawnSync(isWin ? "where.exe" : "which", [name], {
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) return null;
  const lines = (result.stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  return (isWin && lines.find((line) => line.toLowerCase().endsWith(".exe"))) || lines[0] || null;
}

/** Name usable with `spawn(…, { shell: false })` - Windows needs the full path for shims. */
export function resolveExecutable(name) {
  if (process.platform !== "win32") return name;
  return findExecutable(name) || name;
}

/** `[command, args]` for `uv run --directory backend [--extra dev --extra otel] …`. */
export function uvBackend(args, { dev = false } = {}) {
  const extras = dev ? ["--extra", "dev", "--extra", "otel"] : [];
  return [
    resolveExecutable("uv"),
    ["run", "--directory", path.join(ROOT, "backend"), ...extras, ...args],
  ];
}

/** spawnSync from the repo root; exits with the child's status unless `allowFail`. */
export function run(cmd, args, opts = {}) {
  const result = spawnSync(cmd, args, {
    cwd: ROOT,
    encoding: "utf8",
    stdio: opts.inherit ? "inherit" : ["ignore", "pipe", "pipe"],
    shell: false,
    env: { ...process.env, ...opts.env },
  });
  if (result.status !== 0 && !opts.allowFail) {
    if (!opts.inherit) {
      if (result.stdout?.trim()) process.stderr.write(result.stdout);
      if (result.stderr?.trim()) process.stderr.write(result.stderr);
    }
    process.exit(result.status ?? 1);
  }
  return result;
}

/** `node deploy/scripts/llama-serve.mjs <model> <cmd>` with inherited output. */
export function llamaServe(model, cmd, opts = {}) {
  return run(process.execPath, ["deploy/scripts/llama-serve.mjs", model, cmd], {
    inherit: true,
    ...opts,
  });
}

/** `docker compose` args with the given -f files; backend/.env is passed only when it exists. */
export function composeArgs(files, ...parts) {
  const args = ["compose"];
  for (const file of files) args.push("-f", file);
  if (fs.existsSync(BACKEND_ENV)) args.push("--env-file", "backend/.env");
  args.push(...parts);
  return args;
}

export function copyIfMissing(src, dest) {
  if (fs.existsSync(dest)) return false;
  if (!fs.existsSync(src)) {
    console.warn(`warn: missing template ${path.relative(ROOT, src)}`);
    return false;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log(`created ${path.relative(ROOT, dest)}`);
  return true;
}

/** Set or append KEY=value lines in an existing env file. */
export function setEnvKeys(filePath, sets) {
  if (!fs.existsSync(filePath)) return;
  let body = fs.readFileSync(filePath, "utf8");
  for (const [key, value] of Object.entries(sets)) {
    const re = new RegExp(`^${key}=.*$`, "m");
    if (re.test(body)) body = body.replace(re, `${key}=${value}`);
    else body += `\n${key}=${value}\n`;
  }
  fs.writeFileSync(filePath, body);
}

/** False when `key` in `filePath` is false/0/no; a missing file or key yields `fallback`. */
export function envFlag(filePath, key, fallback) {
  if (!fs.existsSync(filePath)) return fallback;
  const raw = (parseEnvFile(filePath)[key] ?? String(fallback)).trim().toLowerCase();
  return raw !== "false" && raw !== "0" && raw !== "no";
}

/** Cheap listen check (netstat / lsof) for preflight tables. */
export function portFree(port) {
  if (process.platform === "win32") {
    const r = spawnSync("netstat", ["-ano"], { encoding: "utf8", shell: false });
    return !new RegExp(`:${port}\\s+.*?LISTENING`, "i").test(r.stdout || "");
  }
  // lsof exit 1 = nothing listening
  return spawnSync("lsof", ["-i", `TCP:${port}`, "-sTCP:LISTEN"], { shell: false }).status !== 0;
}

export function commandFor(name) {
  if (process.platform !== "win32") return name;
  return name === "pnpm" ? "pnpm.cmd" : name;
}

export function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    out[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim();
  }
  return out;
}

export function runtimeEnv(...files) {
  const fileEnv = {};
  for (const file of files) {
    Object.assign(fileEnv, parseEnvFile(file));
  }
  return { ...fileEnv, ...process.env };
}

export async function fetchProbe(url, timeoutMs = 5000, init = {}) {
  const started = Date.now();
  try {
    const res = await fetch(url, {
      ...init,
      signal: init.signal ?? AbortSignal.timeout(timeoutMs),
    });
    const text = await res.text();
    return {
      ok: res.ok,
      status: res.status,
      ms: Date.now() - started,
      detail: text.slice(0, 160).replace(/\s+/g, " ").trim(),
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      ms: Date.now() - started,
      detail: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function fetchOk(url, timeoutMs = 5000, init = {}) {
  return (await fetchProbe(url, timeoutMs, init)).ok;
}

export function listenerInfos(port) {
  if (process.platform !== "win32") {
    const result = spawnSync(
      "sh",
      ["-c", `lsof -nP -iTCP:${port} -sTCP:LISTEN 2>/dev/null || true`],
      {
        encoding: "utf8",
        shell: false,
      }
    );
    return (result.stdout || "")
      .trim()
      .split(/\r?\n/)
      .filter(Boolean)
      .map((line) => ({ pid: "", name: "", commandLine: line, missing: false }));
  }

  const commandText = [
    `$ids = Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique;`,
    "if ($ids) { foreach ($id in $ids) {",
    '$p = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue;',
    'if ($p) { Write-Output ("{0}`t{1}`t{2}" -f $id, $p.Name, $p.CommandLine) }',
    'else { Write-Output ("{0}`t<missing process>`tpossible stale Windows socket" -f $id) }',
    "} }",
  ].join(" ");
  const result = spawnSync("powershell", ["-NoProfile", "-Command", commandText], {
    encoding: "utf8",
    shell: false,
  });
  return (result.stdout || "")
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const [pid = "", name = "", commandLine = ""] = line.split("\t");
      return { pid, name, commandLine, missing: name === "<missing process>" };
    });
}

export function listenerDetails(port) {
  return listenerInfos(port)
    .map((info) => [info.pid, info.name, info.commandLine].filter(Boolean).join("\t"))
    .join("\n");
}

export function killListenerPort(port) {
  if (process.platform === "win32") {
    const result = spawnSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        `$ids = Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($id in $ids) { if ($id -and $id -ne $PID) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 200; if (Get-Process -Id $id -ErrorAction SilentlyContinue) { taskkill /PID $id /F /T | Out-Null } } }`,
      ],
      { encoding: "utf8", shell: false }
    );
    if (result.stderr?.trim()) process.stderr.write(result.stderr);
    return;
  }
  spawnSync("sh", ["-c", `fuser -k ${port}/tcp 2>/dev/null || true`], { shell: false });
}

export function waitForPortRelease(port, timeoutMs = 3000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!listenerInfos(port).length) return true;
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
  }
  return !listenerInfos(port).length;
}

/** GET `url`; body is parsed JSON when possible, else raw text. */
export async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  return { ok: res.ok, status: res.status, body };
}

/** Poll a local llama-server until `/v1/models` answers (models can take minutes to load). */
export async function waitForLlamaServer(port, { timeoutMs = 600_000 } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const { ok } = await fetchJson(`http://127.0.0.1:${port}/v1/models`);
      if (ok) return true;
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  return false;
}
