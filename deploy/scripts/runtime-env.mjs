import { spawnSync } from "node:child_process";
import fs from "node:fs";

export function resolveExecutable(name) {
  if (process.platform !== "win32") return name;
  const result = spawnSync("where.exe", [name], { encoding: "utf8" });
  if (result.status !== 0) return name;
  return (
    result.stdout
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find(Boolean) || name
  );
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
    const result = spawnSync("sh", ["-c", `lsof -nP -iTCP:${port} -sTCP:LISTEN 2>/dev/null || true`], {
      encoding: "utf8",
      shell: false,
    });
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
      { encoding: "utf8", shell: false },
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
