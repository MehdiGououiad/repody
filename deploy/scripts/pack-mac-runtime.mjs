#!/usr/bin/env node
/**
 * Pack the Mac client runtime zip (no application source).
 *
 *   pnpm client:pack:mac
 * -> dist/repody-mac-runtime-<tag>.zip
 *
 * Contents: Compose + bash CLI + Keycloak realm + env examples.
 * Clients pull Hub images; they never need the monorepo.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const SRC = path.join(ROOT, "deploy/client/mac-runtime");
const REALM_SRC = path.join(ROOT, "deploy/keycloak/realm-repody.json");
const DIST = path.join(ROOT, "dist");
const STAGE_NAME = "repody-mac-runtime";

function readTag() {
  const fromEnv = (process.env.REPODY_IMAGE_TAG || "").trim();
  if (fromEnv) return fromEnv;
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
    return String(pkg.version || "0.1.0");
  } catch {
    return "0.1.0";
  }
}

function rmrf(p) {
  fs.rmSync(p, { recursive: true, force: true });
}

function copyDir(src, dest, { skip = [] } = {}) {
  fs.mkdirSync(dest, { recursive: true });
  for (const name of fs.readdirSync(src)) {
    if (skip.includes(name)) continue;
    const from = path.join(src, name);
    const to = path.join(dest, name);
    const st = fs.statSync(from);
    if (st.isDirectory()) {
      if (name === "logs" || name === ".pids") {
        fs.mkdirSync(to, { recursive: true });
        const keep = path.join(from, ".gitkeep");
        if (fs.existsSync(keep)) fs.copyFileSync(keep, path.join(to, ".gitkeep"));
        continue;
      }
      copyDir(from, to, { skip });
      continue;
    }
    if (name === ".env" || name === "paths.env" || name.endsWith(".log")) continue;
    fs.copyFileSync(from, to);
  }
}

function main() {
  if (!fs.existsSync(SRC)) {
    console.error("missing", SRC);
    process.exit(1);
  }
  if (!fs.existsSync(REALM_SRC)) {
    console.error("missing Keycloak realm:", REALM_SRC);
    process.exit(1);
  }

  const tag = readTag();
  const stage = path.join(DIST, STAGE_NAME);
  const zipName = `repody-mac-runtime-${tag}.zip`;
  const zipPath = path.join(DIST, zipName);

  fs.mkdirSync(DIST, { recursive: true });
  rmrf(stage);
  copyDir(SRC, stage, { skip: [".gitignore"] });

  // Always sync realm from Helm chart (canonical).
  fs.mkdirSync(path.join(stage, "config"), { recursive: true });
  fs.copyFileSync(REALM_SRC, path.join(stage, "config", "realm-repody.json"));

  // Pin VERSION for the client.
  fs.writeFileSync(path.join(stage, "VERSION"), `${tag}\n`, "utf8");

  // Ensure CLI is executable in the tree (zip tools on Windows may drop mode).
  const cli = path.join(stage, "bin", "repody");
  if (fs.existsSync(cli)) {
    try {
      fs.chmodSync(cli, 0o755);
    } catch {
      // Windows may ignore mode
    }
  }

  // VENDOR.txt - what to tell the client
  fs.writeFileSync(
    path.join(stage, "VENDOR.txt"),
    [
      `Repody Mac runtime ${tag}`,
      "",
      "This package contains Compose + scripts only — no application source.",
      "Pull images listed in .env.example (REPODY_BACKEND_IMAGE / REPODY_WEB_IMAGE).",
      "",
      "Client steps:",
      "  chmod +x bin/repody",
      "  ./bin/repody setup",
      "  edit models/paths.env",
      "  ./bin/repody start",
      "",
      "Docs: README.md",
      "",
    ].join("\n"),
    "utf8"
  );

  rmrf(zipPath);

  // Prefer PowerShell Compress-Archive on Windows; zip on Unix.
  const isWin = process.platform === "win32";
  let packed = false;
  if (isWin) {
    const ps = spawnSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        `Compress-Archive -Path '${stage.replace(/'/g, "''")}\\*' -DestinationPath '${zipPath.replace(/'/g, "''")}' -Force`,
      ],
      { encoding: "utf8" }
    );
    packed = ps.status === 0 && fs.existsSync(zipPath);
    if (!packed && ps.stderr) console.error(ps.stderr);
  } else {
    const z = spawnSync("zip", ["-r", zipPath, STAGE_NAME], {
      cwd: DIST,
      encoding: "utf8",
    });
    packed = z.status === 0 && fs.existsSync(zipPath);
    if (!packed && z.stderr) console.error(z.stderr);
  }

  if (!packed) {
    console.error("Failed to create zip. Staged folder kept at:", stage);
    process.exit(1);
  }

  const sizeMb = (fs.statSync(zipPath).size / (1024 * 1024)).toFixed(2);
  console.log(`ok: ${path.relative(ROOT, zipPath)} (${sizeMb} MiB)`);
  console.log(`    staged: ${path.relative(ROOT, stage)}`);
  console.log("Hand the zip to Mac clients — keep the git repo private.");
}

main();
