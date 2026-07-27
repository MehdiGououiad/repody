#!/usr/bin/env node
/**
 * Platform test runner — pyramid layers + unified Markdown/HTML report.
 *
 * Default: unit + integration (excludes live / Playwright).
 * Flags:
 *   --unit-only
 *   --integration-only
 *   --with-live     (requires E2E_STACK=1 or E2E_API_URL)
 *   --with-ui       (Playwright; stack must be up)
 *   --skip-backend
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const reportsDir = join(root, "reports", "platform-tests");
const args = new Set(process.argv.slice(2));

mkdirSync(reportsDir, { recursive: true });

function run(label, command, commandArgs, { env = {}, shell = false } = {}) {
  console.log(`\n=== ${label} ===\n`);
  const started = Date.now();
  const result = spawnSync(command, commandArgs, {
    cwd: root,
    env: { ...process.env, ...env },
    encoding: "utf8",
    shell,
  });
  const elapsedMs = Date.now() - started;
  const output = `${result.stdout || ""}${result.stderr || ""}`;
  const logPath = join(reportsDir, `${label.replace(/\s+/g, "-").toLowerCase()}.log`);
  writeFileSync(logPath, output, "utf8");
  return {
    label,
    ok: result.status === 0,
    status: result.status ?? 1,
    elapsedMs,
    logPath,
    output,
  };
}

function parsePytestSummary(output) {
  const pass = output.match(/(\d+) passed/);
  const fail = output.match(/(\d+) failed/);
  const skip = output.match(/(\d+) skipped/);
  const error = output.match(/(\d+) error/);
  const deselected = output.match(/(\d+) deselected/);
  return {
    passed: pass ? Number(pass[1]) : 0,
    failed: fail ? Number(fail[1]) : 0,
    skipped: skip ? Number(skip[1]) : 0,
    errors: error ? Number(error[1]) : 0,
    deselected: deselected ? Number(deselected[1]) : 0,
  };
}

function parsePlaywrightSummary(output) {
  const m = output.match(/(\d+) passed/);
  const f = output.match(/(\d+) failed/);
  const s = output.match(/(\d+) skipped/);
  return {
    passed: m ? Number(m[1]) : 0,
    failed: f ? Number(f[1]) : 0,
    skipped: s ? Number(s[1]) : 0,
    errors: 0,
    deselected: 0,
  };
}

const results = [];
const stamp = new Date().toISOString();

/** Local stack defaults when running live/UI against `pnpm dev:all`. */
const e2eEnv = {
  E2E_STACK: process.env.E2E_STACK ?? "1",
  E2E_API_URL: process.env.E2E_API_URL ?? "http://127.0.0.1:8000",
  E2E_WEB_URL: process.env.E2E_WEB_URL ?? "http://localhost:3000",
  E2E_AUTH_URL: process.env.E2E_AUTH_URL ?? "http://127.0.0.1:8080",
};

function backendRun(label, pytestArgs, extraEnv = {}) {
  return run(
    label,
    process.execPath,
    [
      join(root, "scripts", "backend-run.mjs"),
      "--dev",
      "pytest",
      ...pytestArgs,
      "--tb=short",
    ],
    { env: extraEnv },
  );
}

const junit = (name) => `--junitxml=${join(reportsDir, `junit-${name}.xml`)}`;
const htmlReport = (name) => [
  `--html=${join(reportsDir, `pytest-${name}.html`)}`,
  "--self-contained-html",
];

if (!args.has("--skip-backend")) {
  if (args.has("--unit-only")) {
    results.push(
      backendRun("backend-unit", ["tests/unit", "-q", junit("unit"), ...htmlReport("unit")]),
    );
  } else if (args.has("--integration-only")) {
    results.push(
      backendRun("backend-integration", [
        "tests/integration",
        "-q",
        "-m",
        "not live",
        junit("integration"),
        ...htmlReport("integration"),
      ]),
    );
  } else {
    results.push(
      backendRun("backend-unit", [
        "tests/unit",
        "-q",
        "-m",
        "not live and not slow",
        junit("unit"),
        ...htmlReport("unit"),
      ]),
    );
    results.push(
      backendRun("backend-integration", [
        "tests/integration",
        "-q",
        "-m",
        "not live and not slow",
        junit("integration"),
        ...htmlReport("integration"),
      ]),
    );
  }

  if (args.has("--with-live")) {
    results.push(
      backendRun(
        "backend-live",
        [
          "tests/live",
          "-v",
          "-m",
          "live",
          junit("live"),
          ...htmlReport("live"),
        ],
        e2eEnv,
      ),
    );
  }
}

if (args.has("--with-ui")) {
  results.push(
    run(
      "playwright-ui",
      process.platform === "win32" ? "pnpm.cmd" : "pnpm",
      ["exec", "playwright", "test", "--reporter=list", "--reporter=html"],
      { shell: true, env: e2eEnv },
    ),
  );
}

const rows = results.map((r) => {
  const summary =
    r.label === "playwright-ui"
      ? parsePlaywrightSummary(r.output)
      : parsePytestSummary(r.output);
  const infraDown =
    /ConnectionRefusedError|could not connect|OperationalError/i.test(r.output) &&
    summary.passed === 0;
  return { ...r, summary, infraDown };
});

const overallOk = rows.every((r) => r.ok);
const totalPassed = rows.reduce((n, r) => n + r.summary.passed, 0);
const totalFailed = rows.reduce((n, r) => n + r.summary.failed + r.summary.errors, 0);
const totalSkipped = rows.reduce((n, r) => n + r.summary.skipped, 0);
const infraNotes = rows
  .filter((r) => r.infraDown)
  .map(
    (r) =>
      `- **${r.label}**: Postgres/Redis not reachable — start stack with \`pnpm dev\` then re-run.`,
  );

const md = `# Platform test report

Generated: **${stamp}**

## Verdict

${overallOk ? "**PASS**" : "**FAIL**"} — ${totalPassed} passed, ${totalFailed} failed, ${totalSkipped} skipped

${infraNotes.length ? `## Infrastructure\n\n${infraNotes.join("\n")}\n` : ""}
## Layers

| Layer | Result | Passed | Failed | Skipped | Duration |
|-------|--------|--------|--------|---------|----------|
${rows
  .map((r) => {
    const sec = (r.elapsedMs / 1000).toFixed(1);
    return `| ${r.label} | ${r.ok ? "PASS" : "FAIL"} | ${r.summary.passed} | ${r.summary.failed + r.summary.errors} | ${r.summary.skipped} | ${sec}s |`;
  })
  .join("\n")}

## Artifacts

- Directory: \`reports/platform-tests/\`
- HTML summary: \`index.html\`
- pytest-html: \`pytest-unit.html\`, \`pytest-integration.html\`${args.has("--with-live") ? ", \`pytest-live.html\`" : ""}
- JUnit XML: \`junit-*.xml\`
- Logs: \`*.log\`
${args.has("--with-ui") ? "- Playwright HTML: \`e2e/report/\`\n" : ""}

## Pyramid

| Layer | Path | Command |
|-------|------|---------|
| Unit | \`backend/tests/unit/\` | \`pnpm test:unit\` |
| Integration | \`backend/tests/integration/\` | \`pnpm test:integration\` |
| Live API | \`backend/tests/live/\` | \`pnpm test:live\` |
| UI E2E | \`e2e/tests/\` | \`pnpm test:e2e\` |
| Full report | — | \`pnpm test:platform:report\` |

See [docs/TESTING.md](../../docs/TESTING.md).
`;

const reportPath = join(reportsDir, "REPORT.md");
writeFileSync(reportPath, md, "utf8");

const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><title>Platform test report</title>
<style>
body{font-family:ui-sans-serif,system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}
.pass{color:#0a7} .fail{color:#c22} table{border-collapse:collapse;width:100%}
td,th{border:1px solid #ddd;padding:.5rem;text-align:left} th{background:#f6f6f6}
</style></head><body>
<h1>Platform test report</h1>
<p>${stamp}</p>
<p class="${overallOk ? "pass" : "fail"}"><strong>${overallOk ? "PASS" : "FAIL"}</strong> —
${totalPassed} passed, ${totalFailed} failed, ${totalSkipped} skipped</p>
<table><thead><tr><th>Layer</th><th>Result</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Duration</th></tr></thead>
<tbody>
${rows
  .map((r) => {
    const sec = (r.elapsedMs / 1000).toFixed(1);
    return `<tr><td>${r.label}</td><td class="${r.ok ? "pass" : "fail"}">${r.ok ? "PASS" : "FAIL"}</td><td>${r.summary.passed}</td><td>${r.summary.failed + r.summary.errors}</td><td>${r.summary.skipped}</td><td>${sec}s</td></tr>`;
  })
  .join("\n")}
</tbody></table>
<p>Markdown: <code>reports/platform-tests/REPORT.md</code></p>
</body></html>`;

writeFileSync(join(reportsDir, "index.html"), html, "utf8");

console.log(`\nReport written to ${reportPath}\n`);
console.log(md);
process.exit(overallOk ? 0 : 1);
