#!/usr/bin/env node
/**
 * Production stress test — enqueue 1000 real extraction runs inside the API pod.
 *
 * Prerequisites:
 *   - Workers scaled (merge deploy/client/lab/values.stress-test.yaml and sync)
 *   - External VLM / llama-server reachable from worker-extract pods
 *   - Optional: OIDC token via STRESS_BEARER or --token
 *
 * Usage:
 *   pnpm stress:prod
 *   pnpm stress:prod -- --count 200 --strict
 *   pnpm stress:prod -- --count 50 --skip-invalid --timeout-seconds 3600
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [profile = "full", ...rawExtra] = process.argv.slice(2);
const extra = rawExtra[0] === "--" ? rawExtra.slice(1) : rawExtra;
const ns = process.env.REPODY_K8S_NAMESPACE ?? "repody";
const apiDeploy = process.env.REPODY_API_DEPLOY ?? "deploy/repody-api";
const apiPod = process.env.REPODY_API_POD ?? "";

function kubectl(args, opts = {}) {
  return spawnSync("kubectl", args, { encoding: "utf8", shell: false, ...opts });
}

function resolveApiPod() {
  if (apiPod) return apiPod;
  const res = kubectl([
    "get",
    "pod",
    "-n",
    ns,
    "-l",
    "app.kubernetes.io/component=control,app.kubernetes.io/instance=repody",
    "-o",
    "jsonpath={.items[0].metadata.name}",
  ]);
  if (res.status !== 0 || !res.stdout?.trim()) {
    console.error("Could not resolve API pod. Set REPODY_API_POD or ensure repody-api is running.");
    process.exit(1);
  }
  return res.stdout.trim();
}

function copyIntoPod(local, pod, remote) {
  const data = fs.readFileSync(local);
  const res = spawnSync("kubectl", ["exec", "-i", "-n", ns, pod, "--", "sh", "-c", `cat > ${remote}`], {
    input: data,
    stdio: ["pipe", "inherit", "inherit"],
    shell: false,
  });
  if (res.status !== 0) {
    throw new Error(`kubectl exec copy exited ${res.status ?? 1}`);
  }
}

function syncStressScripts(pod) {
  const files = [
    "backend/scripts/prod_stress_test.py",
    "backend/scripts/benchmark_dev_stress.py",
    "backend/scripts/benchmark_ui_route.py",
  ];
  for (const rel of files) {
    const local = path.join(root, rel);
    const remote = `/app/scripts/${path.basename(rel)}`;
    if (!fs.existsSync(local)) {
      console.error(`Missing local script: ${local}`);
      process.exit(1);
    }
    try {
      copyIntoPod(local, pod, remote);
    } catch (err) {
      console.error(`Failed to copy ${rel}: ${err.message}`);
      process.exit(1);
    }
  }

  const pdfLocal = path.join(root, "e2e/fixtures/documents/Facture.pdf");
  if (fs.existsSync(pdfLocal)) {
    try {
      copyIntoPod(pdfLocal, pod, "/tmp/Facture.pdf");
    } catch (err) {
      console.error(`Failed to copy Facture.pdf: ${err.message}`);
      process.exit(1);
    }
  }
}

function fetchClusterToken() {
  const inline = `
from audit_workbench.auth.keycloak_token import fetch_password_grant_token_sync
print(fetch_password_grant_token_sync(
    token_url='http://keycloak:8080/realms/repody/protocol/openid-connect/token',
    client_id='repody-web',
    client_secret='repody-web-dev-secret',
    username='operator@repody.local',
    password='repody-dev',
    timeout=30.0,
))
`.trim();
  const res = kubectl(["exec", "-n", ns, apiDeploy, "--", "python", "-c", inline]);
  if (res.status !== 0 || !res.stdout?.trim()) {
    return process.env.STRESS_BEARER ?? process.env.E2E_BEARER ?? "";
  }
  return res.stdout.trim();
}

const podDoc = "/tmp/Facture.pdf";
const minioBase = process.env.STRESS_MINIO_UPLOAD_BASE ?? "http://repody-data-minio:9000";
const base = [
  "python",
  "scripts/prod_stress_test.py",
  "--api",
  "http://127.0.0.1:8000",
  "--document",
  podDoc,
  "--minio-upload-base",
  minioBase,
];

const profiles = {
  smoke: [...base, "--in-cluster-auth", "--count", "20", "--concurrency", "4", "--timeout-seconds", "3600"],
  full: [...base, "--in-cluster-auth", "--count", "1000", "--concurrency", "24", "--strict"],
};

const script = profiles[profile] ?? (profile === "custom" ? base : null);
if (!script) {
  console.error(`Unknown stress profile: ${profile}`);
  console.error(`Available: ${Object.keys(profiles).join(", ")}, custom`);
  console.error("Pass prod_stress_test.py flags after -- (e.g. node scripts/prod-stress.mjs custom -- --count 50)");
  process.exit(1);
}

const pod = resolveApiPod();
syncStressScripts(pod);

const useInClusterAuth = !process.env.STRESS_BEARER && !process.env.E2E_BEARER;
const tokenArgs = useInClusterAuth
  ? script.includes("--in-cluster-auth")
    ? []
    : ["--in-cluster-auth"]
  : ["--bearer-token", process.env.STRESS_BEARER ?? process.env.E2E_BEARER ?? fetchClusterToken()];

const result = kubectl(["exec", "-n", ns, apiDeploy, "--", ...script, ...tokenArgs, ...extra], {
  stdio: "inherit",
});
const exitCode = result.status ?? 1;

const reportLocal = path.join(root, "benchmark-reports", "prod-stress.json");
fs.mkdirSync(path.dirname(reportLocal), { recursive: true });
const pull = spawnSync(
  "kubectl",
  ["exec", "-n", ns, apiDeploy, "--", "cat", "/tmp/prod-stress.json"],
  { encoding: "buffer", shell: false },
);
if (pull.status === 0 && pull.stdout?.length) {
  fs.writeFileSync(reportLocal, pull.stdout);
  console.log(`\nLocal report copy: ${reportLocal}`);
}

process.exit(exitCode);
