#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const [profile = "full", ...rawExtra] = process.argv.slice(2);
const extra = rawExtra[0] === "--" ? rawExtra.slice(1) : rawExtra;
const ns = process.env.REPODY_K8S_NAMESPACE ?? "repody";
const apiDeploy = process.env.REPODY_API_DEPLOY ?? "deploy/repody-api";

const scripts = {
  quick: ["python", "scripts/benchmark_suite.py", "--profile", "quick"],
  models: ["python", "scripts/benchmark_suite.py", "--profile", "models"],
  full: ["python", "scripts/benchmark_suite.py", "--profile", "full"],
  "document-models": [
    "python",
    "scripts/benchmark_document_models.py",
    "/app/e2e/fixtures/documents/Facture.pdf",
  ],
};

const script = scripts[profile];
if (!script) {
  console.error(`Unknown benchmark profile: ${profile}`);
  console.error(`Available: ${Object.keys(scripts).join(", ")}`);
  process.exit(1);
}

const result = spawnSync(
  "kubectl",
  ["exec", "-n", ns, apiDeploy, "--", ...script, ...extra],
  { stdio: "inherit", shell: false },
);
process.exit(result.status ?? 1);
