#!/usr/bin/env node
/**
 * Merge scanner JSON outputs into dist/security/report.md + report.json.
 * Used by CI (security workflow) and local security-scan.mjs.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = resolve(root, "dist/security");

const COMPARISON = `
## Scanner comparison (Trivy vs Grype)

| Dimension | Trivy v0.72+ | Grype v0.110+ |
|-----------|--------------|---------------|
| OS packages (Alpine/Debian) | Yes | Yes |
| Language lockfiles (npm, pip, etc.) | Yes | Yes (via Syft SBOM) |
| Container images | Yes | Yes |
| IaC misconfig (Dockerfile, Compose, K8s) | **Yes** | No |
| Secret scanning | **Yes** | No |
| License policy | **Yes** | Limited |
| SBOM input (SPDX/CycloneDX) | Yes | **Primary path** |
| GitHub SARIF + Security tab | **Native** | Via action |
| Pairs with existing Syft release | Optional | **Yes (recommended)** |

**Verdict:** Trivy is the more **complete single tool** for CI gates. Grype is the best **second opinion** on Syft SBOMs already produced at release. Repody gates on both for images and uses Trivy alone for repo/IaC/secret coverage.
`.trim();

function readJson(name) {
  const path = resolve(outDir, name);
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return { _parseError: true, _file: name };
  }
}

function listJson(prefix) {
  if (!existsSync(outDir)) return [];
  return readdirSync(outDir)
    .filter((f) => f.startsWith(prefix) && f.endsWith(".json"))
    .sort();
}

function trivyFindings(doc) {
  if (!doc || doc._parseError) return [];
  const results = doc.Results ?? [];
  const out = [];
  for (const r of results) {
    for (const v of r.Vulnerabilities ?? []) {
      out.push({
        id: v.VulnerabilityID ?? v.ID,
        pkg: v.PkgName,
        severity: v.Severity,
        title: v.Title ?? v.Description?.slice(0, 120),
        fixed: v.FixedVersion ?? "",
        source: "trivy",
      });
    }
    for (const m of r.Misconfigurations ?? []) {
      out.push({
        id: m.ID ?? m.AVDID,
        pkg: m.Type,
        severity: m.Severity,
        title: m.Title ?? m.Message?.slice(0, 120),
        fixed: "",
        source: "trivy-misconfig",
      });
    }
    for (const s of r.Secrets ?? []) {
      out.push({
        id: s.RuleID ?? "secret",
        pkg: s.Category,
        severity: s.Severity ?? "HIGH",
        title: s.Title ?? "Secret detected",
        fixed: "",
        source: "trivy-secret",
      });
    }
  }
  return out;
}

function grypeFindings(doc) {
  if (!doc || doc._parseError) return [];
  const matches = doc.matches ?? [];
  return matches.map((m) => ({
    id: m.vulnerability?.id,
    pkg: m.artifact?.name,
    severity: m.vulnerability?.severity,
    title: m.vulnerability?.description?.slice(0, 120),
    fixed: m.vulnerability?.fix?.versions?.join(", ") ?? "",
    source: "grype",
  }));
}

function pnpmFindings(doc) {
  if (!doc?.advisories) return [];
  const out = [];
  for (const [id, adv] of Object.entries(doc.advisories)) {
    out.push({
      id: adv.cves?.[0] ?? id,
      pkg: adv.module_name,
      severity: adv.severity?.toUpperCase() ?? "UNKNOWN",
      title: adv.title ?? adv.overview?.slice(0, 120),
      fixed: adv.patched_versions ?? "",
      source: "pnpm-audit",
    });
  }
  return out;
}

function pipAuditFindings(doc) {
  if (!Array.isArray(doc)) return [];
  return doc.map((row) => ({
    id: row.id ?? row.aliases?.[0],
    pkg: row.name,
    severity: (row.severity ?? "UNKNOWN").toUpperCase(),
    title: row.description?.slice(0, 120) ?? row.id,
    fixed: row.fix_versions?.join(", ") ?? "",
    source: "pip-audit",
  }));
}

function gateSeverity(sev) {
  const s = String(sev ?? "").toUpperCase();
  return s === "CRITICAL" || s === "HIGH";
}

function section(title, findings) {
  const gated = findings.filter((f) => gateSeverity(f.severity));
  const lines = [
    `### ${title}`,
    "",
    `Total: ${findings.length} · Gate (CRITICAL/HIGH): **${gated.length}**`,
    "",
  ];
  if (gated.length === 0) {
    lines.push("_No CRITICAL/HIGH findings._", "");
    return { lines, gated };
  }
  lines.push("| Severity | ID | Package | Source | Fix |");
  lines.push("|----------|-----|---------|--------|-----|");
  for (const f of gated.slice(0, 50)) {
    lines.push(
      `| ${f.severity} | ${f.id ?? "—"} | ${f.pkg ?? "—"} | ${f.source} | ${f.fixed || "—"} |`,
    );
  }
  if (gated.length > 50) {
    lines.push("", `_…and ${gated.length - 50} more (see JSON artifacts)._`);
  }
  lines.push("");
  return { lines, gated };
}

export function buildSecurityReport() {
  mkdirSync(outDir, { recursive: true });

  const allFindings = [];
  const sections = [];

  const pnpm = readJson("pnpm-audit.json");
  const pip = readJson("pip-audit.json");
  const pnpmF = pnpmFindings(pnpm);
  const pipF = pipAuditFindings(pip);
  sections.push(section("Dependency audits", [...pnpmF, ...pipF]));
  allFindings.push(...pnpmF, ...pipF);

  const trivyFiles = [
    ...listJson("trivy-fs"),
    ...listJson("trivy-config"),
    ...listJson("trivy-secret"),
    ...listJson("trivy-image-"),
  ];
  const trivyAll = [];
  for (const f of trivyFiles) {
    trivyAll.push(...trivyFindings(readJson(f)));
  }
  sections.push(section("Trivy (filesystem, IaC, secrets, images)", trivyAll));
  allFindings.push(...trivyAll);

  const grypeAll = [];
  for (const f of listJson("grype-")) {
    grypeAll.push(...grypeFindings(readJson(f)));
  }
  sections.push(section("Grype (Syft SBOM on container images)", grypeAll));
  allFindings.push(...grypeAll);

  const gatedTotal = allFindings.filter((f) => gateSeverity(f.severity));
  const status = gatedTotal.length === 0 ? "PASS" : "FAIL";

  const md = [
    "# Repody security scan report",
    "",
    `**Status:** ${status}`,
    `**Generated:** ${new Date().toISOString()}`,
    `**Gate:** CRITICAL + HIGH (unfixed only for Trivy/Grype)`,
    "",
    COMPARISON,
    "",
    "## Summary",
    "",
    "| Scanner | Findings | CRITICAL/HIGH |",
    "|---------|----------|---------------|",
    `| pnpm audit | ${pnpmF.length} | ${pnpmF.filter((f) => gateSeverity(f.severity)).length} |`,
    `| pip-audit | ${pipF.length} | ${pipF.filter((f) => gateSeverity(f.severity)).length} |`,
    `| Trivy | ${trivyAll.length} | ${trivyAll.filter((f) => gateSeverity(f.severity)).length} |`,
    `| Grype | ${grypeAll.length} | ${grypeAll.filter((f) => gateSeverity(f.severity)).length} |`,
    `| **Total (deduped by id+pkg)** | — | **${gatedTotal.length}** |`,
    "",
    "",
    "## Details",
    "",
    ...sections.flatMap((s) => s.lines),
    "## Artifacts",
    "",
    "Raw JSON under `dist/security/`. SARIF files upload to GitHub Security on CI.",
    "",
  ].join("\n");

  const reportJson = {
    generatedAt: new Date().toISOString(),
    status,
    gate: { severities: ["CRITICAL", "HIGH"] },
    comparison: {
      primary: "trivy",
      secondary: "grype",
      rationale:
        "Trivy is the more complete standalone scanner; Grype validates Syft SBOMs from release pipeline.",
    },
    counts: {
      pnpm: pnpmF.length,
      pip: pipF.length,
      trivy: trivyAll.length,
      grype: grypeAll.length,
      gated: gatedTotal.length,
    },
    findings: allFindings,
  };

  writeFileSync(resolve(outDir, "report.md"), md, "utf8");
  writeFileSync(resolve(outDir, "report.json"), JSON.stringify(reportJson, null, 2), "utf8");

  if (process.env.GITHUB_STEP_SUMMARY) {
    writeFileSync(process.env.GITHUB_STEP_SUMMARY, md, "utf8");
  }

  return { status, gatedTotal: gatedTotal.length, reportPath: resolve(outDir, "report.md") };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const { status, gatedTotal, reportPath } = buildSecurityReport();
  console.log(`Report: ${reportPath}`);
  console.log(`Gated findings: ${gatedTotal}`);
  process.exit(status === "PASS" ? 0 : 1);
}
