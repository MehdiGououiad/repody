#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import {
  LOCAL_ADDONS,
  LOCAL_CREDENTIALS,
  LOCAL_HOSTS,
  localUrl,
} from "./k8s-local-common.mjs";

const NS = "repody-app";
const NS_QUEUE = "repody-queue";
const LOCAL_ARGO_APPS = [
  "repody-local-data",
  "repody-local-queue",
  "repody-local-auth",
  "repody-local-app",
];
const ARGO_NS = "argocd";
const WITH_OBS =
  process.argv.includes("--with=obs") ||
  ["1", "true", "yes"].includes(
    String(process.env.REPODY_K8S_LOCAL_OBS ?? "").toLowerCase(),
  );

function run(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, {
    encoding: "utf8",
    shell: false,
    ...options,
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function must(label, cmd, args, options = {}) {
  const result = run(cmd, args, options);
  if (result.status !== 0) {
    throw new Error(
      `${label} failed\n${result.stdout}${result.stderr}`.trim(),
    );
  }
  return result.stdout.trim();
}

function optional(cmd, args, options = {}) {
  const result = run(cmd, args, options);
  return result.status === 0 ? result.stdout.trim() : "";
}

function curl(args) {
  return must("curl", process.platform === "win32" ? "curl.exe" : "curl", args);
}

async function step(label, fn) {
  process.stderr.write(`\n▶ ${label}\n`);
  try {
    const detail = await fn();
    process.stderr.write(`✓ ${label}${detail ? ` — ${detail}` : ""}\n`);
  } catch (error) {
    failures.push([label, String(error?.message || error)]);
    process.stderr.write(`✗ ${label}\n${String(error?.message || error)}\n`);
  }
}

const failures = [];
const warnings = [];

function parseJson(text) {
  return JSON.parse(text.replace(/^\uFEFF/, ""));
}

function gatewayCurl(host, pathName, extra = []) {
  return curl([
    "-fsS",
    "--max-time",
    "10",
    "-H",
    `Host: ${host}`,
    ...extra,
    `http://127.0.0.1${pathName}`,
  ]);
}

function tokenFor(username) {
  const body = [
    "grant_type=password",
    `client_id=${LOCAL_CREDENTIALS.keycloakClientId}`,
    `client_secret=${LOCAL_CREDENTIALS.keycloakClientSecret}`,
    `username=${encodeURIComponent(username)}`,
    `password=${LOCAL_CREDENTIALS.keycloakPassword}`,
  ].join("&");
  const raw = curl([
    "-fsS",
    "--max-time",
    "10",
    "-H",
    `Host: ${LOCAL_HOSTS.auth}`,
    "-H",
    "Content-Type: application/x-www-form-urlencoded",
    "--data",
    body,
    "http://127.0.0.1/realms/repody/protocol/openid-connect/token",
  ]);
  const token = parseJson(raw).access_token;
  if (!token) throw new Error("Keycloak token response had no access_token");
  return token;
}

await step("Kubernetes context", () => {
  const ctx = must("kubectl context", "kubectl", ["config", "current-context"]);
  if (ctx !== "kind-repody-local") {
    warnings.push(`current kubectl context is ${ctx}, expected kind-repody-local`);
  }
  return ctx;
});

await step("Repody pods ready", () => {
  const json = must("pods", "kubectl", ["-n", NS, "get", "pods", "-o", "json"]);
  const pods = parseJson(json).items;
  const notReady = pods.filter((pod) => {
    const phase = pod.status?.phase;
    if (phase === "Succeeded") return false;
    const statuses = [
      ...(pod.status?.initContainerStatuses ?? []),
      ...(pod.status?.containerStatuses ?? []),
    ];
    return phase !== "Running" || statuses.some((status) => !status.ready && status.state?.terminated?.reason !== "Completed");
  });
  if (notReady.length) {
    throw new Error(notReady.map((pod) => `${pod.metadata.name}:${pod.status.phase}`).join(", "));
  }
  return `${pods.length} pods`;
});

await step("Gateway and HTTPRoutes", () => {
  const programmed = must("gateway", "kubectl", [
    "-n",
    NS,
    "get",
    "gateway/repody",
    "-o",
    "jsonpath={.status.listeners[0].conditions[?(@.type=='Programmed')].status}",
  ]);
  if (programmed !== "True") throw new Error(`Gateway Programmed=${programmed}`);
  const routes = must("routes", "kubectl", [
    "-n",
    NS,
    "get",
    "httproute",
    "-o",
    "json",
  ]);
  for (const route of parseJson(routes).items) {
    const accepted = route.status?.parents
      ?.flatMap((parent) => parent.conditions ?? [])
      ?.find((condition) => condition.type === "Accepted");
    const refs = route.status?.parents
      ?.flatMap((parent) => parent.conditions ?? [])
      ?.find((condition) => condition.type === "ResolvedRefs");
    if (accepted?.status !== "True" || refs?.status !== "True") {
      throw new Error(`HTTPRoute not accepted: ${route.metadata.name}`);
    }
  }
  return "Programmed=True";
});

await step("API health through Gateway", () => {
  const live = parseJson(gatewayCurl(LOCAL_HOSTS.api, "/v1/healthz/live"));
  const ready = parseJson(gatewayCurl(LOCAL_HOSTS.api, "/v1/healthz"));
  if (live.status !== "ok" || ready.status !== "ok") {
    throw new Error(`live=${live.status} ready=${ready.status}`);
  }
  if (!ready.hatchetConfigured || ready.storageBackend !== "s3" || ready.queueBackend !== "hatchet") {
    throw new Error(`unexpected readiness payload: ${JSON.stringify(ready)}`);
  }
  return `queue=${ready.queueBackend}, storage=${ready.storageBackend}`;
});

await step("Frontend and Auth.js provider", () => {
  const dashboard = run(process.platform === "win32" ? "curl.exe" : "curl", [
    "-sS",
    "-o",
    process.platform === "win32" ? "NUL" : "/dev/null",
    "-w",
    "%{http_code} %{redirect_url}",
    "-H",
    `Host: ${LOCAL_HOSTS.web}`,
    "http://127.0.0.1/dashboard",
  ]);
  if (
    dashboard.status !== 0 ||
    !dashboard.stdout.includes(`307 ${localUrl(LOCAL_HOSTS.web, "/login")}`)
  ) {
    throw new Error(`dashboard did not redirect to login: ${dashboard.stdout}${dashboard.stderr}`);
  }
  const providers = parseJson(gatewayCurl(LOCAL_HOSTS.web, "/api/auth/providers"));
  if (!providers.keycloak) throw new Error("Auth.js Keycloak provider missing");
  const temp = mkdtempSync(path.join(tmpdir(), "repody-auth-"));
  const cookie = path.join(temp, "cookies.txt");
  const csrf = parseJson(
    curl([
      "-fsS",
      "-c",
      cookie,
      "-b",
      cookie,
      "-H",
      `Host: ${LOCAL_HOSTS.web}`,
      "http://127.0.0.1/api/auth/csrf",
    ]),
  ).csrfToken;
  const signIn = run(process.platform === "win32" ? "curl.exe" : "curl", [
    "-sS",
    "-o",
    process.platform === "win32" ? "NUL" : "/dev/null",
    "-w",
    "%{http_code} %{redirect_url}",
    "-c",
    cookie,
    "-b",
    cookie,
    "-H",
    `Host: ${LOCAL_HOSTS.web}`,
    "-H",
    "Content-Type: application/x-www-form-urlencoded",
    "--data",
    `csrfToken=${encodeURIComponent(csrf)}&callbackUrl=${encodeURIComponent(localUrl(LOCAL_HOSTS.web, "/dashboard"))}`,
    "http://127.0.0.1/api/auth/signin/keycloak",
  ]);
  if (signIn.status !== 0 || !signIn.stdout.includes(`302 ${localUrl(LOCAL_HOSTS.auth, "/realms/repody/")}`)) {
    throw new Error(`Auth.js sign-in did not redirect to Keycloak: ${signIn.stdout}${signIn.stderr}`);
  }
  return "login redirect + Keycloak redirect";
});

await step("Keycloak token and authenticated API", () => {
  const token = tokenFor(LOCAL_CREDENTIALS.keycloakUser);
  const me = parseJson(
    gatewayCurl(LOCAL_HOSTS.api, "/v1/iam/me", [
      "-H",
      `Authorization: Bearer ${token}`,
    ]),
  );
  if (!me.roles?.includes("operator")) throw new Error(`operator role missing: ${JSON.stringify(me)}`);
  const workflows = parseJson(
    gatewayCurl(LOCAL_HOSTS.api, "/v1/workflows", [
      "-H",
      `Authorization: Bearer ${token}`,
    ]),
  );
  if (!Array.isArray(workflows.workflows)) throw new Error("workflow list shape invalid");
  return `roles=${me.roles.join(",")}`;
});

await step("Database and Redis from API pod", () => {
  const code = `
import asyncio, os
async def main():
    import asyncpg
    import redis.asyncio as redis
    db = os.environ["AUDIT_DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db)
    print("db", (await conn.fetchval("select version()")).split()[0])
    await conn.close()
    r = redis.from_url(os.environ["AUDIT_REDIS_URL"])
    print("redis", await r.ping())
    await r.aclose()
asyncio.run(main())
`;
  const result = spawnSync("kubectl", ["-n", NS, "exec", "-i", "deploy/repody-api", "--", "python", "-"], {
    input: code,
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  if (!result.stdout.includes("redis True")) throw new Error(result.stdout);
  return result.stdout.trim().replace(/\s+/g, " ");
});

await step("MinIO presign, Gateway PUT, and confirm", () => {
  const token = tokenFor(LOCAL_CREDENTIALS.keycloakUser);
  const temp = mkdtempSync(path.join(tmpdir(), "repody-upload-"));
  const pdf = path.join(temp, "smoke.pdf");
  const bytes = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n", "ascii");
  writeFileSync(pdf, bytes);
  const body = path.join(temp, "presign.json");
  writeFileSync(
    body,
    JSON.stringify({ files: [{ fileName: "smoke.pdf", mimeType: "application/pdf", size: bytes.length }] }),
  );
  const presign = parseJson(
    curl([
      "-fsS",
      "-H",
      `Host: ${LOCAL_HOSTS.api}`,
      "-H",
      `Authorization: Bearer ${token}`,
      "-H",
      "Content-Type: application/json",
      "--data-binary",
      `@${body}`,
      "http://127.0.0.1/v1/uploads/presign",
    ]),
  );
  const upload = presign.uploads?.[0];
  if (!upload?.uploadUrl || !upload?.storageKey) throw new Error(JSON.stringify(presign));
  curl([
    "-fsS",
    "--resolve",
    `${LOCAL_HOSTS.files}:80:127.0.0.1`,
    "-H",
    "Content-Type: application/pdf",
    "--upload-file",
    pdf,
    upload.uploadUrl,
  ]);
  const confirm = path.join(temp, "confirm.json");
  writeFileSync(confirm, JSON.stringify({ storageKeys: [upload.storageKey] }));
  const confirmed = parseJson(
    curl([
      "-fsS",
      "-H",
      `Host: ${LOCAL_HOSTS.api}`,
      "-H",
      `Authorization: Bearer ${token}`,
      "-H",
      "Content-Type: application/json",
      "--data-binary",
      `@${confirm}`,
      "http://127.0.0.1/v1/uploads/confirm",
    ]),
  );
  if (confirmed.uploads?.[0]?.storageKey !== upload.storageKey) {
    throw new Error(JSON.stringify(confirmed));
  }
  return upload.storageKey;
});

await step("Hatchet UI and workers", () => {
  must("hatchet", "kubectl", [
    "-n",
    NS_QUEUE,
    "exec",
    "deploy/repody-hatchet-api",
    "--",
    "sh",
    "-c",
    "wget -q -O - http://127.0.0.1:8080/api/ready",
  ]);
  for (const name of ["repody-worker-fast", "repody-worker-ocr"]) {
    const logs = must(`${name} logs`, "kubectl", ["-n", NS, "logs", `deploy/${name}`, "--tail=120"]);
    if (
      !logs.includes("started, waiting for tasks") &&
      !logs.includes("action listener established")
    ) {
      throw new Error(`${name} is not connected to Hatchet`);
    }
  }
  return "API ready + fast/ocr workers";
});

await step("Argo CD installed", () => {
  const summaries = [];
  for (const appName of LOCAL_ARGO_APPS) {
    const app = must(`argocd app ${appName}`, "kubectl", [
      "-n",
      ARGO_NS,
      "get",
      `applications.argoproj.io/${appName}`,
      "-o",
      "json",
    ]);
    const parsed = parseJson(app);
    const health = parsed.status?.health?.status ?? "Unknown";
    const sync = parsed.status?.sync?.status ?? "Unknown";
    const comparison = parsed.status?.conditions?.find(
      (condition) => condition.type === "ComparisonError",
    );
    if (comparison) {
      warnings.push(`Argo CD ${appName} comparison blocked: ${comparison.message}`);
    }
    summaries.push(`${appName}: health=${health}, sync=${sync}`);
  }
  const server = optional("kubectl", [
    "-n",
    ARGO_NS,
    "get",
    "deploy/argocd-server",
    "-o",
    "jsonpath={.status.readyReplicas}",
  ]);
  if (Number(server) < 1) {
    throw new Error("argocd-server is not ready");
  }
  return `${summaries.join("; ")}, server=ready`;
});

await step("Observability/Bugsink addon presence", () => {
  if (!WITH_OBS) return "skipped (--with=obs not enabled)";
  const all = must("cluster resources", "kubectl", ["get", "pods,svc", "-A"]);
  const missing = [];
  for (const token of LOCAL_ADDONS) {
    if (!all.toLowerCase().includes(token)) missing.push(token);
  }
  if (missing.length) throw new Error(`missing ${missing.join(", ")}`);
  const grafana = parseJson(gatewayCurl(LOCAL_HOSTS.grafana, "/api/health"));
  if (grafana.database !== "ok") throw new Error(`Grafana unhealthy: ${JSON.stringify(grafana)}`);
  const otelEnabled = optional("kubectl", [
    "-n",
    NS,
    "exec",
    "deploy/repody-api",
    "--",
    "printenv",
    "AUDIT_OTEL_ENABLED",
  ]);
  const otelEndpoint = optional("kubectl", [
    "-n",
    NS,
    "exec",
    "deploy/repody-api",
    "--",
    "printenv",
    "AUDIT_OTEL_EXPORTER_ENDPOINT",
  ]);
  if (otelEnabled !== "true") {
    warnings.push("App OTEL export is disabled; observability addons are installed, but traces are not emitted by repody-api.");
  } else if (!otelEndpoint.includes("/v1/traces")) {
    throw new Error(`OTEL endpoint misconfigured: ${otelEndpoint}`);
  }
  const tempoPorts = must("Tempo service ports", "kubectl", [
    "-n",
    NS,
    "get",
    "svc/local-tempo",
    "-o",
    "json",
  ]);
  const tempo = parseJson(tempoPorts);
  if (!tempo.spec.ports.some((port) => port.name === "otlp-grpc" && port.port === 4317)) {
    throw new Error("Tempo OTLP gRPC port 4317 is not exposed");
  }
  const hatchetSecret = parseJson(must("Hatchet shared config", "kubectl", [
    "-n",
    NS_QUEUE,
    "get",
    "secret/hatchet-shared-config",
    "-o",
    "json",
  ]));
  const decodeSecret = (key) =>
    Buffer.from(hatchetSecret.data?.[key] ?? "", "base64").toString("utf8");
  const hatchetCollector = decodeSecret("SERVER_OTEL_COLLECTOR_URL");
  const hatchetInsecure = decodeSecret("SERVER_OTEL_INSECURE");
  if (hatchetCollector !== "local-tempo.repody-app.svc.cluster.local:4317") {
    throw new Error(`Hatchet OTEL collector misconfigured: ${hatchetCollector}`);
  }
  if (hatchetInsecure !== "true") {
    throw new Error(`Hatchet OTEL insecure flag misconfigured: ${hatchetInsecure}`);
  }
  const hatchetDeploys = parseJson(must("Hatchet deployments", "kubectl", [
    "-n",
    NS_QUEUE,
    "get",
    "deploy/repody-hatchet-api",
    "deploy/repody-hatchet-engine",
    "-o",
    "json",
  ]));
  const serviceNames = new Map();
  for (const item of hatchetDeploys.items) {
    const env = item.spec.template.spec.containers[0].env ?? [];
    const serviceName = env.find((entry) => entry.name === "SERVER_OTEL_SERVICE_NAME")?.value;
    serviceNames.set(item.metadata.name, serviceName);
  }
  if (serviceNames.get("repody-hatchet-api") !== "hatchet-api") {
    throw new Error("Hatchet API OTEL service name is not hatchet-api");
  }
  if (serviceNames.get("repody-hatchet-engine") !== "hatchet-engine") {
    throw new Error("Hatchet engine OTEL service name is not hatchet-engine");
  }
  const bugsink = gatewayCurl(LOCAL_HOSTS.bugsink, "/accounts/login/");
  if (!bugsink.toLowerCase().includes("bugsink")) throw new Error("Bugsink UI did not render");
  const code = `
import urllib.request
for name, url in {
    "loki": "http://local-loki:3100/ready",
    "tempo": "http://local-tempo:3200/ready",
    "loki_labels": "http://local-loki:3100/loki/api/v1/labels",
}.items():
    with urllib.request.urlopen(url, timeout=10) as response:
        body = response.read().decode("utf-8", "replace")
        print(name, response.status, body[:120].replace("\\n", " "))
`;
  const result = spawnSync("kubectl", ["-n", NS, "exec", "-i", "deploy/repody-api", "--", "python", "-"], {
    input: code,
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) throw new Error(result.stdout + result.stderr);
  return `OTEL=${otelEnabled || "unset"}, Hatchet OTEL=gRPC, Grafana/Loki/Promtail/Tempo/Bugsink`;
});

if (warnings.length) {
  process.stderr.write("\nWarnings:\n");
  for (const warning of warnings) process.stderr.write(`- ${warning}\n`);
}

if (failures.length) {
  process.stderr.write("\nSmoke test failed:\n");
  for (const [label, error] of failures) {
    process.stderr.write(`- ${label}: ${error.split("\n")[0]}\n`);
  }
  process.exit(1);
}

process.stderr.write("\n✓ Local Kubernetes core smoke passed.\n");
