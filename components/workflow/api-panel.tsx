"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import {
  Copy, Check, Eye, EyeOff, Play, Zap,
  ChevronLeft, ExternalLink,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import { runWorkflowApi, type RunProgress } from "@/lib/api/test-run";
import {
  RunDetailedReportSections,
  RunStatusBanner,
  type RunReportLabels,
} from "@/components/audit/run-report/run-report-core";
import type { RunAuditDetail } from "@/lib/types/audit";
import { reportClientError } from "@/lib/report-error";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import { buildWorkflowRunSnippets, workflowDocumentSlots } from "@/lib/api/workflow-run-snippets";
import { IngestionSection } from "@/components/workflow/ingestion-section";
import type { DocumentDef } from "@/lib/types";

// ── types ─────────────────────────────────────────────────────────────────────

type RunReport = RunAuditDetail & { processedAt: string };

// ── helpers ───────────────────────────────────────────────────────────────────

function useCopy(timeout = 1800) {
  const [copied, setCopied] = useState(false);
  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), timeout);
    });
  };
  return { copied, copy };
}

function CopyButton({ text, className }: { text: string; className?: string }) {
  const tCommon = useTranslations("common");
  const { copied, copy } = useCopy();
  return (
    <button
      type="button"
      onClick={() => copy(text)}
      aria-label={copied ? tCommon("copied") : tCommon("copy")}
      className={cn(
        "inline-flex items-center gap-1 text-[10px] font-mono transition-colors shrink-0",
        copied ? "text-success" : "text-on-surface-variant hover:text-on-surface",
        className
      )}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? tCommon("copied") : tCommon("copy")}
    </button>
  );
}

// ── Info screen ───────────────────────────────────────────────────────────────

function InfoScreen({
  workflowId,
  workflowName,
  apiKey,
  apiKeyHint,
  documents,
  onRun,
  filesByDocId,
  onFilesChange,
}: {
  workflowId: string;
  workflowName: string;
  apiKey: string;
  apiKeyHint?: string;
  documents: DocumentDef[];
  onRun: () => void;
  filesByDocId: Record<string, File>;
  onFilesChange: (files: Record<string, File>) => void;
}) {
  const t = useTranslations("workflows.builder.api");
  const [showKey, setShowKey] = useState(false);
  const [activeTab, setActiveTab] = useState<"curl" | "python" | "js">("curl");
  const mounted = useHydrated();

  const endpoint = mounted
    ? `${window.location.origin}/api/v1/workflows/${workflowId}/runs`
    : `/api/v1/workflows/${workflowId}/runs`;
  const hasFullKey = isFullWorkflowApiKey(apiKey);
  const maskedKey =
    apiKeyHint ||
    (apiKey.length > 12 ? `${apiKey.slice(0, 12)}********` : apiKey || "—");
  const displayKey = showKey && hasFullKey ? apiKey : maskedKey;
  const snippetKey = hasFullKey ? apiKey : maskedKey;
  const slots = workflowDocumentSlots(documents);
  const hasFiles = Object.keys(filesByDocId).length > 0;
  const canRun = hasFullKey && hasFiles;
  const snippets = buildWorkflowRunSnippets({
    endpoint,
    apiKey: snippetKey,
    documents,
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Badge variant="success" className="gap-1.5">
          <span className="size-1.5 rounded-full bg-success animate-pulse" />
          {t("live")}
        </Badge>
        <span className="text-xs text-on-surface-variant">{t("isDeployed", { name: workflowName })}</span>
      </div>

      {/* Endpoint card */}
      <div className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border flex items-center gap-2 bg-surface-container-low">
          <Zap className="h-3.5 w-3.5 text-primary" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">{t("endpointLabel")}</span>
        </div>
        <div className="p-4 space-y-2.5">
          <div className="flex items-center gap-2 rounded-lg bg-surface-container-lowest border border-border px-3 py-2">
            <span className="text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded font-mono shrink-0">POST</span>
            <code translate="no" className="flex-1 text-[11px] font-mono text-on-surface truncate">{endpoint}</code>
            <CopyButton text={endpoint} />
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-surface-container-lowest border border-border px-3 py-2">
            <span className="text-[10px] font-semibold text-on-surface-variant uppercase tracking-wide shrink-0">{t("keyLabel")}</span>
            <code translate="no" className="flex-1 text-[11px] font-mono text-on-surface truncate">{displayKey}</code>
            <button
              type="button"
              onClick={() => setShowKey((v) => !v)}
              aria-label={showKey ? t("hideKey") : t("showKey")}
              className="text-on-surface-variant hover:text-on-surface transition-colors shrink-0"
            >
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
            <CopyButton text={hasFullKey ? apiKey : maskedKey} />
          </div>
        </div>
      </div>

      {slots.length > 0 ? (
        <div className="panel-elevated rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-border bg-surface-container-low">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
              {t("documentSlotsLabel")}
            </span>
          </div>
          <div className="p-4 space-y-2">
            <p className="text-xs text-on-surface-variant leading-relaxed">{t("schemaHint")}</p>
            <ul className="space-y-2">
              {slots.map((doc, index) => {
                const fieldCount = doc.schema.filter((f) => f.name.trim()).length;
                return (
                  <li
                    key={doc.id}
                    className="rounded-lg border border-border bg-surface-container-lowest px-3 py-2 text-xs"
                  >
                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                      <span className="font-mono text-[10px] text-on-surface-variant shrink-0">
                        {index + 1}.
                      </span>
                      <span className="font-semibold text-on-surface truncate">
                        {doc.documentType.trim()}
                      </span>
                      <span className="text-on-surface-variant">
                        {t("fieldsCount", { count: fieldCount })}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="text-[11px] text-on-surface-variant leading-relaxed">{t("pollHint")}</p>
          </div>
        </div>
      ) : null}

      {/* Code snippets */}
      <div className="panel-elevated rounded-xl overflow-hidden">
        <div className="flex items-center border-b border-border" role="tablist" aria-label={t("endpointLabel")}>
          {(["curl", "python", "js"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 text-xs font-medium transition-colors uppercase tracking-wide",
                activeTab === tab ? "border-b-2 border-primary text-primary" : "text-on-surface-variant hover:text-on-surface"
              )}
            >
              {tab}
            </button>
          ))}
          <div className="flex-1" />
          <CopyButton text={snippets[activeTab]} className="mr-4" />
        </div>
        <pre className="p-4 text-[11px] font-mono text-on-surface overflow-x-auto leading-relaxed bg-surface-container-lowest whitespace-pre-wrap break-all">
          <code translate="no">{snippets[activeTab]}</code>
        </pre>
      </div>

      {/* Run test CTA */}
      <div className="panel-elevated rounded-xl p-4 space-y-3 min-w-0">
        <div>
          <Label className="text-xs font-semibold text-on-surface-variant">
            {slots.length > 1 ? t("testDocumentsLabel") : t("testDocumentLabel")}
          </Label>
          <p className="text-[11px] text-on-surface-variant mt-1 leading-relaxed">
            {t("testUploadHint")}
          </p>
        </div>
        <IngestionSection
          documents={documents}
          rules={[]}
          uploads={{}}
          filesByDocId={filesByDocId}
          onFilesChange={onFilesChange}
        />
        {!hasFiles ? (
          <p className="text-[11px] text-warning">{t("testUploadRequired")}</p>
        ) : null}
        {!hasFullKey ? (
          <p className="text-[11px] text-warning">{t("keyUnavailable")}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={onRun}
        disabled={!canRun}
        className="group flex items-center justify-between w-full rounded-xl border-2 border-dashed border-accent-blue/40 bg-accent-blue/5 hover:bg-accent-blue/10 hover:border-accent-blue/70 transition-[border-color,background-color] px-5 py-4 disabled:opacity-50 disabled:pointer-events-none"
      >
        <div className="text-left">
          <p className="text-sm font-semibold text-primary">{t("runTest")}</p>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("runTestHint")}</p>
        </div>
        <div className="size-9 rounded-full bg-primary/15 group-hover:bg-primary/25 flex items-center justify-center transition-colors shrink-0 ml-4">
          <Play className="h-4 w-4 text-primary" />
        </div>
      </button>
    </div>
  );
}

// ── Loading screen ────────────────────────────────────────────────────────────

function LoadingScreen({
  workflowName,
  progress,
}: {
  workflowName: string;
  progress: RunProgress | null;
}) {
  const t = useTranslations("workflows.builder.api");
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[360px] gap-6 text-center px-4">
      <div className="relative size-16">
        <div className="absolute inset-0 rounded-full border-4 border-primary/20" />
        <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Zap className="h-6 w-6 text-primary" />
        </div>
      </div>
      <div>
        <p className="text-sm font-semibold text-on-surface">{t("processing")}</p>
        <p className="text-xs text-on-surface-variant mt-1">{t("processingHint", { name: workflowName })}</p>
      </div>
      {progress ? (
        <div className="w-full max-w-md text-left">
          <RunProgressSteps progress={progress} />
        </div>
      ) : (
        <p className="text-xs text-on-surface-variant">{t("parseStep")}…</p>
      )}
    </div>
  );
}

// ── Report screen ─────────────────────────────────────────────────────────────

function apiReportLabels(
  t: ReturnType<typeof useTranslations>,
  report?: RunReport
): RunReportLabels {
  return {
    allPassed: t("allPassed"),
    validationFailed: t("validationFailed"),
    reviewRequired: t("reviewRequired"),
    fieldsExtracted: report
      ? t("fieldsExtracted", { count: report.summary.fieldsExtracted })
          .replace(String(report.summary.fieldsExtracted), "")
          .trim()
      : undefined,
    rulesPassed: report
      ? t("rulesPassed", { passed: report.summary.passed, total: report.summary.total })
      : undefined,
    rulesFailed: report
      ? t("rulesFailed", { count: report.summary.failed }).replace(String(report.summary.failed), "").trim()
      : undefined,
    docExtracted: (done, total) => t("docExtracted", { done, total }),
    statusPassed: t("statusPassed"),
    expected: t("expected"),
    got: t("got"),
    extractedData: t("extractedData"),
    validationResults: t("validationResults"),
  };
}

function ReportScreen({ report, onBack }: { report: RunReport; onBack: () => void }) {
  const t = useTranslations("workflows.builder.api");
  const locale = useLocale();
  const labels = apiReportLabels(t, report);
  const ts = new Date(report.processedAt).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="flex flex-col gap-5">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-xs text-on-surface-variant hover:text-on-surface transition-colors self-start"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        {t("backToApi")}
      </button>

      <RunStatusBanner
        audit={report}
        labels={labels}
        subtitle={`${report.workflowName} · ${ts}`}
      />

      <Link
        href={`/audits/${report.id}`}
        className="flex items-center justify-between w-full rounded-xl border border-accent-blue/30 bg-accent-blue/5 hover:bg-accent-blue/10 transition-colors px-4 py-3 group"
      >
        <div>
          <p className="text-sm font-semibold text-primary">{t("viewFullReport")}</p>
          <p className="text-xs text-on-surface-variant mt-0.5">
            {report.id} · {t("shareable")}
          </p>
        </div>
        <ExternalLink className="h-4 w-4 text-primary shrink-0 group-hover:translate-x-0.5 transition-transform" />
      </Link>

      <RunDetailedReportSections audit={report} locale={locale} labels={labels} />
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

type Screen = "info" | "loading" | "report";

export function ApiPanel({
  workflowId,
  workflowName,
  apiKey,
  apiKeyHint,
  documents,
}: {
  workflowId: string;
  workflowName: string;
  apiKey: string;
  apiKeyHint?: string;
  documents: DocumentDef[];
}) {
  const [screen, setScreen] = useState<Screen>("info");
  const [report, setReport] = useState<RunReport | null>(null);
  const [filesByDocId, setFilesByDocId] = useState<Record<string, File>>({});
  const [runProgress, setRunProgress] = useState<RunProgress | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const run = async () => {
    if (Object.keys(filesByDocId).length === 0) return;
    setScreen("loading");
    setRunProgress(null);
    setRunError(null);
    try {
      const detail = await runWorkflowApi(
        workflowId,
        apiKey,
        { documents, filesByDocId },
        (progress) => setRunProgress(progress)
      );
      setReport({ ...detail, processedAt: detail.createdAt });
      setScreen("report");
    } catch (e) {
      reportClientError(e, { workflowId, surface: "api-panel" });
      setRunError(e instanceof Error ? e.message : "Run failed");
      setScreen("info");
    }
  };

  if (screen === "loading") {
    return <LoadingScreen workflowName={workflowName} progress={runProgress} />;
  }
  if (screen === "report" && report) {
    return <ReportScreen report={report} onBack={() => setScreen("info")} />;
  }

  return (
    <>
      {runError ? (
        <div className="rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger mb-4">
          {runError}
        </div>
      ) : null}
      <InfoScreen
        workflowId={workflowId}
        workflowName={workflowName}
        apiKey={apiKey}
        apiKeyHint={apiKeyHint}
        documents={documents}
        onRun={run}
        filesByDocId={filesByDocId}
        onFilesChange={setFilesByDocId}
      />
    </>
  );
}
