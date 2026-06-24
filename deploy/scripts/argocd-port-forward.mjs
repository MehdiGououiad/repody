#!/usr/bin/env node
/**
 * Port-forward Argo CD to http(s)://localhost:8080 (vanilla install, no Gateway).
 */
import { spawn, spawnSync } from "node:child_process";
import {
  ARGO_NAMESPACE,
  argoLocalBaseUrl,
  readArgoPortForwardTarget,
} from "./argocd-local.mjs";

function captureOptional(cmd, args) {
  const result = spawnSync(cmd, args, { encoding: "utf8", shell: false });
  return result.status === 0 ? result.stdout.trim() : null;
}

const target = readArgoPortForwardTarget(captureOptional);

console.error(`Argo CD → ${argoLocalBaseUrl(target)}`);
console.error(
  '  admin password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d',
);

const child = spawn(
  "kubectl",
  [
    "port-forward",
    "svc/argocd-server",
    "-n",
    ARGO_NAMESPACE,
    `${target.localPort}:${target.remotePort}`,
  ],
  { stdio: "inherit", shell: process.platform === "win32" },
);

child.on("exit", (code) => process.exit(code ?? 0));

process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
