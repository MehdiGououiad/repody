#!/usr/bin/env node
/**
 * Detect local IPv4 and write PUBLIC_HOST + CORS/MinIO settings into .env for LAN sharing.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { networkInterfaces } from "node:os";
import { join } from "node:path";

function pickLanIp() {
  const nets = networkInterfaces();
  const candidates = [];
  for (const name of Object.keys(nets)) {
    for (const net of nets[name] ?? []) {
      if (net.family !== "IPv4" || net.internal) continue;
      if (net.address.startsWith("169.254.")) continue;
      candidates.push({ name, address: net.address });
    }
  }
  const preferred = candidates.find((c) => /^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[01])\./.test(c.address));
  return preferred?.address ?? candidates[0]?.address ?? null;
}

function upsertEnvLine(lines, key, value) {
  const prefix = `${key}=`;
  const idx = lines.findIndex((line) => line.startsWith(prefix));
  const next = `${key}=${value}`;
  if (idx >= 0) lines[idx] = next;
  else lines.push(next);
}

const ip = pickLanIp();
if (!ip) {
  console.error("Could not detect a LAN IPv4 address.");
  process.exit(1);
}

const envPath = join(process.cwd(), ".env");
let raw = "";
try {
  raw = readFileSync(envPath, "utf8").replace(/^\uFEFF/, "");
} catch {
  console.error("Missing .env — copy from .env.example first.");
  process.exit(1);
}

const lines = raw.split(/\r?\n/).filter((line, i, arr) => !(i === arr.length - 1 && line === ""));
upsertEnvLine(lines, "PUBLIC_HOST", ip);
upsertEnvLine(lines, "AUDIT_MINIO_PUBLIC_ENDPOINT", `${ip}:9000`);

const utf8 = new TextEncoder();
writeFileSync(envPath, `${lines.join("\n")}\n`, { encoding: "utf8" });

console.log(`Configured LAN sharing:`);
console.log(`  PUBLIC_HOST=${ip}`);
console.log(`  App URL:     http://${ip}:3000`);
console.log(`  MinIO:       http://${ip}:9000 (presigned uploads)`);
console.log("");
console.log("Next: pnpm docker:deploy:lan");
console.log("Allow inbound TCP 3000 and 9000 in Windows Firewall if peers cannot connect.");
