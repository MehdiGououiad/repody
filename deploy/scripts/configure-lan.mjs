#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import { networkInterfaces } from "node:os";
import { join } from "node:path";

function pickLanIp() {
  const nets = networkInterfaces();
  /** @type {{ address: string; score: number }[]} */
  const candidates = [];

  for (const name of Object.keys(nets)) {
    const lower = name.toLowerCase();
    const isVirtual =
      lower.includes("wsl") ||
      lower.includes("hyper-v") ||
      lower.includes("docker") ||
      lower.includes("vethernet") ||
      lower.includes("virtualbox") ||
      lower.includes("vmware") ||
      lower.includes("loopback");

    for (const net of nets[name] ?? []) {
      if (net.family !== "IPv4" || net.internal) continue;
      if (net.address.startsWith("169.254.")) continue;

      let score = 0;
      if (/^192\.168\./.test(net.address)) score += 40;
      if (/^10\./.test(net.address)) score += 30;
      if (/^172\.(1[6-9]|2\d|3[01])\./.test(net.address)) score += 20;
      if (lower.includes("wi-fi") || lower.includes("wifi") || lower.includes("ethernet")) {
        score += 25;
      }
      if (isVirtual) score -= 50;
      candidates.push({ address: net.address, score });
    }
  }

  candidates.sort((a, b) => b.score - a.score);
  return candidates[0]?.address ?? null;
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

function loadEnvLines(file) {
  try {
    const raw = readFileSync(join(process.cwd(), file), "utf8").replace(/^\uFEFF/, "");
    return raw.split(/\r?\n/).filter((line, i, arr) => !(i === arr.length - 1 && line === ""));
  } catch {
    return null;
  }
}

const envPath = join(process.cwd(), ".env");
const envLines = loadEnvLines(".env");
if (!envLines) {
  console.error("Missing .env — copy from .env.example first.");
  process.exit(1);
}

const lanKeys = {
  PUBLIC_HOST: ip,
  AUDIT_MINIO_PUBLIC_ENDPOINT: `${ip}:9000`,
  AUTH_URL: `http://${ip}:3000`,
  AUTH_KEYCLOAK_ISSUER: `http://${ip}:8080/realms/repody`,
  AUDIT_OIDC_ISSUER: `http://${ip}:8080/realms/repody`,
  KEYCLOAK_HOSTNAME: ip,
};

for (const [key, value] of Object.entries(lanKeys)) {
  upsertEnvLine(envLines, key, value);
}
writeFileSync(envPath, `${envLines.join("\n")}\n`, { encoding: "utf8" });

const localPath = join(process.cwd(), ".env.local");
const localLines = loadEnvLines(".env.local") ?? [];
for (const [key, value] of Object.entries(lanKeys)) {
  if (key === "PUBLIC_HOST" || key === "AUDIT_MINIO_PUBLIC_ENDPOINT" || key === "KEYCLOAK_HOSTNAME") {
    continue;
  }
  upsertEnvLine(localLines, key, value);
}
writeFileSync(localPath, `${localLines.join("\n")}\n`, { encoding: "utf8" });

console.log(`Configured LAN: PUBLIC_HOST=${ip}`);
console.log(`  App:      http://${ip}:3000`);
console.log(`  API:      http://${ip}:8000`);
console.log(`  Keycloak: http://${ip}:8080`);
console.log(`  MinIO:    http://${ip}:9000`);
console.log("");
console.log("Dev with auth:");
console.log("  pnpm dev -- --auth --warmup --logs --rebuild --lan");
console.log("");
console.log(
  "Prod: pnpm compose up --stack=prod --lan --build --force-recreate=api,web,minio"
);
console.log("");
console.log("Windows Firewall (run PowerShell as Administrator):");
console.log(
  `  New-NetFirewallRule -DisplayName "Repody LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000,8000,8080,9000`
);
