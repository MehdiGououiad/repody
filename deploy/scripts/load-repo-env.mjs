import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/** @param {string} value */
function unquote(value) {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/** Merge repo-root `.env` / `.env.local` into a target env object (later files win). */
export function loadRepoEnv(target = process.env) {
  const env = { ...target };
  for (const file of [".env", ".env.local"]) {
    const path = join(process.cwd(), file);
    if (!existsSync(path)) continue;
    const raw = readFileSync(path, "utf8").replace(/^\uFEFF/, "");
    for (const line of raw.split(/\r?\n/)) {
      if (!line || line.startsWith("#")) continue;
      const idx = line.indexOf("=");
      if (idx < 1) continue;
      const key = line.slice(0, idx).trim();
      env[key] = unquote(line.slice(idx + 1));
    }
  }
  return env;
}
