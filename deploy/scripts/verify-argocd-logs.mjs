#!/usr/bin/env node
/**
 * Verify Argo CD pod log API (standalone install via port-forward).
 */
import { spawn, spawnSync } from "node:child_process";
import { ARGO_NAMESPACE, argoLocalBaseUrl, readArgoPortForwardTarget } from "./argocd-local.mjs";

function capture(cmd, args) {
  const result = spawnSync(cmd, args, { encoding: "utf8", shell: false });
  if (result.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} failed: ${result.stderr || result.stdout}`);
  }
  return result.stdout.trim();
}

function captureOptional(cmd, args) {
  const result = spawnSync(cmd, args, { encoding: "utf8", shell: false });
  return result.status === 0 ? result.stdout.trim() : null;
}

function curl(args) {
  const result = spawnSync("curl.exe", args, { encoding: "utf8", shell: false });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const target = readArgoPortForwardTarget(captureOptional);
const base = argoLocalBaseUrl(target);
const tlsFlags = target.tlsInsecure ? ["-k"] : [];

const password = Buffer.from(
  capture("kubectl", [
    "-n",
    ARGO_NAMESPACE,
    "get",
    "secret",
    "argocd-initial-admin-secret",
    "-o",
    "jsonpath={.data.password}",
  ]),
  "base64",
).toString();

const pod = capture("kubectl", [
  "-n",
  "repody-app",
  "get",
  "pods",
  "-l",
  "app.kubernetes.io/component=control",
  "-o",
  "jsonpath={.items[0].metadata.name}",
]);

const portForward = spawn(
  "kubectl",
  [
    "port-forward",
    "svc/argocd-server",
    "-n",
    ARGO_NAMESPACE,
    `${target.localPort}:${target.remotePort}`,
  ],
  { stdio: "ignore", shell: false },
);

try {
  await sleep(4000);

  const sessionRes = curl([
    ...tlsFlags,
    "-s",
    "-X",
    "POST",
    "-H",
    "Content-Type: application/json",
    "-d",
    JSON.stringify({ username: "admin", password }),
    `${base}/api/v1/session`,
  ]);
  if (sessionRes.status !== 0 || !sessionRes.stdout.trim()) {
    console.error("session failed:", sessionRes.stderr || sessionRes.stdout);
    process.exit(1);
  }
  const { token } = JSON.parse(sessionRes.stdout);

  const query = new URLSearchParams({
    appNamespace: "argocd",
    namespace: "repody-app",
    podName: pod,
    container: "api",
    tailLines: "20",
    follow: "false",
  });

  const logsRes = curl([
    "-s",
    ...tlsFlags,
    "-w",
    "\n__HTTP__%{http_code}",
    "-H",
    `Authorization: Bearer ${token}`,
    `${base}/api/v1/applications/repody-local-app/logs?${query}`,
  ]);

  const marker = logsRes.stdout.lastIndexOf("\n__HTTP__");
  const body = marker >= 0 ? logsRes.stdout.slice(0, marker) : logsRes.stdout;
  const httpMatch = logsRes.stdout.match(/__HTTP__(\d{3})$/);
  const httpCode = httpMatch?.[1] ?? "000";

  console.error(`> Argo CD logs API: HTTP ${httpCode}, ${body.length} bytes`);
  if (httpCode !== "200" || !body.trim()) {
    console.error(body.slice(0, 500));
    process.exit(1);
  }

  console.error("ok: Argo CD returned application pod logs");
  console.log(body.slice(0, 400));
} finally {
  portForward.kill("SIGTERM");
}
