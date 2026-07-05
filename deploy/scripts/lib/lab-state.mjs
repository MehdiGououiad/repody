import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

/**
 * Lab runtime state — decouples infra (Harbor/Argo CD) from Repody platform pushes.
 * @param {string} runtimeDir
 */
export function createLabState(runtimeDir) {
  const statePath = path.join(runtimeDir, "lab-state.json");

  function read() {
    if (!existsSync(statePath)) return {};
    try {
      return JSON.parse(readFileSync(statePath, "utf8"));
    } catch {
      return {};
    }
  }

  function write(partial) {
    mkdirSync(runtimeDir, { recursive: true });
    const next = { ...read(), ...partial, updatedAt: new Date().toISOString() };
    writeFileSync(statePath, JSON.stringify(next, null, 2), "utf8");
    return next;
  }

  function get(key) {
    return read()[key];
  }

  function isFresh(key, maxAgeMs = 86_400_000) {
    const entry = read()[key];
    if (!entry?.installedAt) return false;
    return Date.now() - Date.parse(entry.installedAt) < maxAgeMs;
  }

  return { read, write, get, isFresh, statePath };
}
