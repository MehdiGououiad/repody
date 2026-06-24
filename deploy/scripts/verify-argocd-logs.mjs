#!/usr/bin/env node
/**
 * Verify Argo CD pod log API works through the local Gateway (argocd.repody.local).
 */
import { spawnSync } from "node:child_process";
import { LOCAL_HOSTS } from "./k8s-local-common.mjs";

function capture(cmd, args) {
  const result = spawnSync(cmd, args, { encoding: "utf8", shell: false });
  if (result.status !== 0) {
    throw new Error(`${cmd} ${args.join(" ")} failed: ${result.stderr || result.stdout}`);
  }
  return result.stdout.trim();
}

function curl(args) {
  const result = spawnSync("curl.exe", args, { encoding: "utf8", shell: false });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

const password = Buffer.from(
  capture("kubectl", [
    "-n",
    "argocd",
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

const sessionRes = curl([
  "-sf",
  "-X",
  "POST",
  "-H",
  `Host: ${LOCAL_HOSTS.argocd}`,
  "-H",
  "Content-Type: application/json",
  "-d",
  JSON.stringify({ username: "admin", password }),
  "http://127.0.0.1/api/v1/session",
]);
if (sessionRes.status !== 0) {
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
  "-w",
  "\n__HTTP__%{http_code}",
  "-H",
  `Host: ${LOCAL_HOSTS.argocd}`,
  "-H",
  `Authorization: Bearer ${token}`,
  `http://127.0.0.1/api/v1/applications/repody-local-app/logs?${query}`,
]);

const marker = logsRes.stdout.lastIndexOf("\n__HTTP__");
const body = marker >= 0 ? logsRes.stdout.slice(0, marker) : logsRes.stdout;
const httpMatch = logsRes.stdout.match(/__HTTP__(\d{3})$/);
const httpCode = httpMatch?.[1] ?? "000";

console.error(`> Argo CD logs API via Gateway: HTTP ${httpCode}, ${body.length} bytes`);
if (httpCode !== "200") {
  console.error(body.slice(0, 500));
  process.exit(1);
}

if (!body.trim()) {
  console.error("empty log body — checking direct kubectl logs for comparison");
  const direct = capture("kubectl", ["-n", "repody-app", "logs", pod, "-c", "api", "--tail=3"]);
  console.error("kubectl logs sample:\n", direct);
  process.exit(1);
}

if (!body.includes("http_request") && !body.includes("logging_configured") && !body.includes("level")) {
  console.error("unexpected log body:\n", body.slice(0, 500));
  process.exit(1);
}

console.error("ok: Argo CD returned application pod logs through the Gateway");
console.log(body.slice(0, 400));
