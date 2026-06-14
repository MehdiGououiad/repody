#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const [mode = "docker", ...rawExtra] = process.argv.slice(2);
const extra = rawExtra[0] === "--" ? rawExtra.slice(1) : rawExtra;
const compose = ["compose", "-f", "compose.yaml", "-f", "compose.cpu.yaml"];
const install = "pip install -q pytest pytest-asyncio respx aiosqlite httpx";

const dockerBase = [
  ...compose,
  "run",
  "--rm",
  "--no-deps",
  "-v",
  "./backend/tests:/app/tests",
  "-v",
  "./backend/src:/app/src",
  "-v",
  "./e2e:/app/e2e",
  "--entrypoint",
  "sh",
  "api",
  "-c",
];

const dockerPytest =
  "python -m pytest tests/test_e2e/test_facture_ui_e2e.py -v --tb=short";

const commands = {
  docker: [
    ...dockerBase,
    `${install} && PYTHONPATH=/app:/app/src AUDIT_DATABASE_URL=sqlite+aiosqlite:///:memory: AUDIT_SEED_ON_STARTUP=false AUDIT_RUN_JOBS_INLINE=false AUDIT_EXTRACTION_CACHE_ENABLED=false AUDIT_INFERENCE_MODE=docker_model_runner AUDIT_REPODY_VLM_WARMUP_ON_START=false ${dockerPytest} -m 'e2e_facture and not live'`,
  ],
  stack: [
    ...dockerBase,
    `${install} && PYTHONPATH=/app:/app/src E2E_STACK=1 E2E_API_URL=http://api:8000 FACTURE_PDF=/app/e2e/fixtures/documents/Facture.pdf ${dockerPytest} -m 'e2e_facture and live'`,
  ],
};

const args = commands[mode];
if (!args) {
  console.error(`Unknown facture test mode: ${mode}`);
  console.error(`Available: ${Object.keys(commands).join(", ")}`);
  process.exit(1);
}

const result = spawnSync("docker", [...args, ...extra], {
  stdio: "inherit",
  shell: false,
});
process.exit(result.status ?? 1);
