#!/usr/bin/env node
/**
 * Platform endpoint catalog — printed at startup and via `pnpm compose urls`.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

/** @typedef {'dev' | 'prod' | 'vps'} DeployMode */

/**
 * @param {object} opts
 * @param {DeployMode} opts.mode
 * @param {boolean} [opts.logs]
 * @param {boolean} [opts.traces]
 * @param {boolean} [opts.publicHttps]
 * @param {boolean} [opts.lan]
 * @param {string} [opts.publicDomain]
 * @param {string} [opts.filesDomain]
 * @param {string} [opts.publicHost]
 * @returns {{ role: string; url: string; purpose: string }[]}
 */
export function collectEndpoints(opts) {
  /** @type {{ role: string; url: string; purpose: string }[]} */
  const items = [];

  if (opts.mode === "vps") {
    const app = opts.publicDomain || "app.example.com";
    const files = opts.filesDomain || "files.example.com";
    items.push({
      role: "Web UI",
      url: `https://${app}`,
      purpose: "Audit workbench — workflows, runs, uploads (Caddy basic auth)",
    });
    items.push({
      role: "API health",
      url: `https://${app}/api/v1/healthz`,
      purpose: "Health check via Next.js proxy",
    });
    items.push({
      role: "File uploads",
      url: `https://${files}`,
      purpose: "Browser → MinIO for direct document uploads",
    });
    return items;
  }

  const host =
    opts.lan && opts.publicHost ? opts.publicHost : "localhost";

  if (opts.publicHttps && opts.publicDomain) {
    const app = opts.publicDomain;
    const files = opts.filesDomain || `files.${app}`;
    items.push({
      role: "Web UI",
      url: `https://${app}`,
      purpose: "Audit workbench (Caddy TLS + basic auth)",
    });
    items.push({
      role: "API health",
      url: `https://${app}/api/v1/healthz`,
      purpose: "Health check via Next.js proxy",
    });
    items.push({
      role: "File uploads",
      url: `https://${files}`,
      purpose: "Browser → MinIO over HTTPS",
    });
    return items;
  }

  const webBase = `http://${host}:3000`;
  const apiBase = `http://${host}:8000`;

  items.push({
    role: "Web UI",
    url: webBase,
    purpose: "Next.js app — workflows, runs, document audit",
  });
  items.push({
    role: "API",
    url: apiBase,
    purpose: "FastAPI control plane (runs, uploads, dispatch)",
  });
  items.push({
    role: "API health",
    url: `${apiBase}/v1/healthz/live`,
    purpose: "Liveness probe",
  });
  items.push({
    role: "Hatchet",
    url: `http://${host}:8888`,
    purpose: "Workflow engine UI (ops / debugging)",
  });
  items.push({
    role: "MinIO S3",
    url: `http://${host}:9000`,
    purpose: "Object storage API (uploaded documents)",
  });
  items.push({
    role: "MinIO console",
    url: `http://${host}:9001`,
    purpose: "Bucket admin UI (dev default: minioadmin / minioadmin)",
  });

  if (opts.logs) {
    items.push({
      role: "Grafana",
      url: `http://${host}:3001`,
      purpose: "Platform logs dashboard (admin / audit)",
    });
    items.push({
      role: "Loki",
      url: `http://${host}:3100`,
      purpose: "Log store (query via Grafana)",
    });
  }

  if (opts.traces) {
    items.push({
      role: "Tempo OTLP",
      url: `http://${host}:4318/v1/traces`,
      purpose: "Distributed traces ingest (view in Grafana)",
    });
  }

  return items;
}

/**
 * @param {object} opts
 * @param {DeployMode} opts.mode
 * @param {boolean} [opts.logs]
 * @param {boolean} [opts.traces]
 * @param {boolean} [opts.publicHttps]
 * @param {boolean} [opts.lan]
 * @param {string} [opts.publicDomain]
 * @param {string} [opts.filesDomain]
 * @param {string} [opts.publicHost]
 * @param {string} [opts.footer]
 */
export function formatPlatformBanner(opts) {
  const items = collectEndpoints(opts);
  const width = 70;
  const lines = [
    "═".repeat(width),
    " Platform endpoints",
    "─".repeat(width),
  ];

  for (const { role, url, purpose } of items) {
    lines.push(` ${role.padEnd(14)} ${url}`);
    lines.push(`${"".padEnd(16)}${purpose}`);
  }

  if (opts.footer) {
    lines.push("─".repeat(width));
    lines.push(` ${opts.footer}`);
  }

  lines.push("═".repeat(width));
  return lines.join("\n");
}

/** @param {Parameters<typeof formatPlatformBanner>[0]} opts */
export function printPlatformBanner(opts) {
  console.error(`\n${formatPlatformBanner(opts)}\n`);
}

function envValue(key) {
  try {
    const raw = readFileSync(join(process.cwd(), ".env"), "utf8").replace(/^\uFEFF/, "");
    for (const line of raw.split(/\r?\n/)) {
      if (!line || line.startsWith("#")) continue;
      const idx = line.indexOf("=");
      if (idx < 1) continue;
      if (line.slice(0, idx).trim() === key) {
        return line.slice(idx + 1).trim();
      }
    }
  } catch {
    // optional
  }
  return process.env[key] ?? "";
}

function parseCliArgs(argv) {
  /** @type {Record<string, string | boolean>} */
  const flags = {};
  let mode = "dev";
  for (const arg of argv) {
    if (arg === "dev" || arg === "prod" || arg === "vps") {
      mode = arg;
      continue;
    }
    if (arg.startsWith("--")) {
      const eq = arg.indexOf("=");
      if (eq === -1) flags[arg.slice(2)] = true;
      else flags[arg.slice(2, eq)] = arg.slice(eq + 1);
    }
  }
  return { mode, flags };
}

if (process.argv[1]?.endsWith("platform-urls.mjs")) {
  const { mode, flags } = parseCliArgs(process.argv.slice(2));
  printPlatformBanner({
    mode: /** @type {DeployMode} */ (mode),
    logs: Boolean(flags.logs),
    traces: Boolean(flags.traces),
    publicHttps: Boolean(flags.public),
    lan: Boolean(flags.lan),
    publicDomain: String(flags["public-domain"] || envValue("PUBLIC_DOMAIN") || ""),
    filesDomain: String(flags["files-domain"] || envValue("FILES_DOMAIN") || ""),
    publicHost: String(flags["public-host"] || envValue("PUBLIC_HOST") || ""),
  });
}
