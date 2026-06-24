#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const [mode = "unit", ...rawExtra] = process.argv.slice(2);
const extra = rawExtra[0] === "--" ? rawExtra.slice(1) : rawExtra;

const pytestBase = [
  "python",
  "-m",
  "pytest",
  "tests/test_e2e/test_facture_ui_e2e.py",
  "-v",
  "--tb=short",
];

const commands = {
  unit: {
    cwd: "backend",
    cmd: "uv",
    args: [
      "run",
      ...pytestBase,
      "-m",
      "e2e_facture and not live",
    ],
    env: {
      PYTHONPATH: ".:src",
      AUDIT_DATABASE_URL: "sqlite+aiosqlite:///:memory:",
      AUDIT_SEED_ON_STARTUP: "false",
      AUDIT_RUN_JOBS_INLINE: "false",
      AUDIT_EXTRACTION_CACHE_ENABLED: "false",
      AUDIT_INFERENCE_MODE: "docker_model_runner",
      AUDIT_REPODY_VLM_WARMUP_ON_START: "false",
    },
  },
  live: {
    cwd: "backend",
    cmd: "uv",
    args: [
      "run",
      ...pytestBase,
      "-m",
      "e2e_facture and live",
    ],
    env: {
      PYTHONPATH: ".:src",
      E2E_STACK: "1",
      E2E_API_URL: process.env.E2E_API_URL ?? "http://api.repody.local",
      FACTURE_PDF: "../e2e/fixtures/documents/Facture.pdf",
    },
  },
};

const spec = commands[mode];
if (!spec) {
  console.error(`Unknown facture test mode: ${mode}`);
  console.error(`Available: ${Object.keys(commands).join(", ")}`);
  process.exit(1);
}

const result = spawnSync(spec.cmd, [...spec.args, ...extra], {
  stdio: "inherit",
  cwd: spec.cwd,
  env: { ...process.env, ...spec.env },
  shell: process.platform === "win32",
});
process.exit(result.status ?? 1);
