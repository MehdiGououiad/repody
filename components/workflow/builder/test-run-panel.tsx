"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  AlertCircle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Code,
  ExternalLink,
  FileText,
  FlaskConical,
  Loader2,
  Play,
  Rocket,
  XCircle,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { syncRuleBodies } from "@/lib/rules/sync-rules";
import { ApiPanel } from "@/components/workflow/api-panel";
import { IngestionSection, type UploadedFile } from "@/components/workflow/ingestion-section";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import { TestRunSummaryDetails } from "@/components/workflow/run-details-meta";
import {
  runTestInline,
  runTestWithFiles,
  type ClientStepLabels,
  type RunProgress,
  type TestRunResult,
} from "@/lib/api/test-run";
import { buildClientProgress } from "@/lib/api/client-run-progress";
import { humanizeRunError } from "@/lib/api/api-error";
import {
  isRuleFailure,
  RuleStatusIcon,
  ruleStatusColor,
  ruleStatusLabel,
} from "@/lib/rule-status";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

export type TestPhase = "idle" | "running" | "done";

export interface TestSessionState {
  phase: TestPhase;
  progress: RunProgress | null;
  result: TestRunResult | null;
  error: string | null;
  filesByDocId: Record<string, File>;
  uploadMeta: Record<string, UploadedFile | null>;
}

export const emptyTestSession = (): TestSessionState => ({
  phase: "idle",
  progress: null,
  result: null,
  error: null,
  filesByDocId: {},
  uploadMeta: {},
});

function formatUploadSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function clientStepLabels(t: ReturnType<typeof useTranslations>): ClientStepLabels {
  return {
    "save-workflow": {
      label: t("test.progress.saveWorkflow"),
      pendingDetail: t("test.progress.saveWorkflowDetail"),
    },
    "upload-check": {
      label: t("test.progress.uploadCheck"),
      pendingDetail: t("test.progress.uploadCheckDetail"),
    },
    "upload-reuse": {
      label: t("test.progress.uploadReuse"),
      pendingDetail: t("test.progress.uploadReuseDetail", { files: "{files}" }),
    },
    "upload-presign": {
      label: t("test.progress.uploadPresign"),
      pendingDetail: t("test.progress.uploadPresignDetail"),
    },
    "upload-transfer": {
      label: t("test.progress.uploadTransfer"),
      pendingDetail: t("test.progress.uploadTransferDetail"),
    },
    "upload-confirm": {
      label: t("test.progress.uploadConfirm"),
      pendingDetail: t("test.progress.uploadConfirmDetail"),
    },
    "start-run": {
      label: t("test.progress.startRun"),
      pendingDetail: t("test.progress.startRunDetail"),
    },
    "poll-run": {
      label: t("test.progress.pollRun"),
      pendingDetail: t("test.progress.pollRunDetail"),
    },
  };
}

export function TestRunPanel({
  workflowId,
  documents,
  rules,
  workflowName,
  onBeforeRun,
  session,
  onSessionChange,
  t,
}: {
  workflowId: string;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  workflowName: string;
  onBeforeRun?: () => Promise<string>;
  session: TestSessionState;
  onSessionChange: (patch: Partial<TestSessionState>) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const { phase, progress: runProgress, result, error, filesByDocId, uploadMeta } = session;
  const hasFiles = Object.keys(filesByDocId).length > 0;
  const stepLabels = clientStepLabels(t);

  const runTest = async () => {
    onSessionChange({
      phase: "running",
      progress: buildClientProgress(stepLabels, "save-workflow"),
      error: null,
    });
    try {
      onSessionChange({
        progress: buildClientProgress(stepLabels, "save-workflow"),
      });
      const id = onBeforeRun ? await onBeforeRun() : workflowId;
      const payload = { documents, rules: syncRuleBodies(rules), workflowName };
      const reporter = {
        clientLabels: stepLabels,
        onProgress: (progress: RunProgress) => onSessionChange({ progress }),
      };
      const data = hasFiles
        ? await runTestWithFiles(id, { ...payload, filesByDocId }, reporter)
        : await runTestInline(id, payload, reporter);
      onSessionChange({ result: data, phase: "done", progress: null });
    } catch (e) {
      const raw = e instanceof Error ? e.message : "Failed";
      onSessionChange({
        error: humanizeRunError(raw),
        phase: "idle",
        progress: null,
      });
    }
  };

  const statusColor = {
    passed: "border-success/40 bg-success/5 text-success",
    failed: "border-danger/40 bg-danger/5 text-danger",
    warning: "border-warning/40 bg-warning/5 text-warning",
  } as const;

  const StatusIcon =
    result?.status === "passed"
      ? CheckCircle2
      : result?.status === "failed"
        ? XCircle
        : AlertCircle;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-on-surface">{t("test.uploadTitle")}</h3>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("test.uploadHint")}</p>
        </div>
        <IngestionSection
          documents={documents}
          rules={rules}
          uploads={uploadMeta}
          filesByDocId={filesByDocId}
          onFilesChange={(files) => {
            const docIds = new Set(documents.map((d) => d.id));
            const nextMeta: Record<string, UploadedFile | null> = { ...uploadMeta };
            for (const id of Object.keys(nextMeta)) {
              if (!docIds.has(id) || !(id in files)) delete nextMeta[id];
            }
            for (const [id, file] of Object.entries(files)) {
              nextMeta[id] = { name: file.name, size: formatUploadSize(file.size) };
            }
            onSessionChange({ filesByDocId: files, uploadMeta: nextMeta });
          }}
        />
        <Button className="w-full gap-2" onClick={runTest} disabled={phase === "running"}>
          {phase === "running" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {phase === "running" ? t("test.running") : t("test.runBtn")}
        </Button>
        {!hasFiles && phase === "idle" && (
          <p className="text-[11px] text-on-surface-variant text-center">
            {t("test.noFilesHint")}
          </p>
        )}
        {error && (
          <div
            role="alert"
            className="rounded-lg border border-danger/40 bg-danger/5 px-3 py-2.5 text-left space-y-1"
          >
            <p className="text-xs font-semibold text-danger">{t("test.errorTitle")}</p>
            <p className="text-xs text-danger-strong leading-relaxed">{error}</p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-on-surface">{t("test.resultsTitle")}</h3>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("test.resultsHint")}</p>
        </div>

        {phase === "idle" && !result && (
          <div className="flex flex-col items-center justify-center h-48 rounded-xl border-2 border-dashed border-accent-blue/30 text-center gap-3 panel-elevated">
            <FlaskConical className="h-8 w-8 text-on-surface-variant/30" />
            <p className="text-sm text-on-surface-variant">{t("test.idle")}</p>
            <p className="text-xs text-on-surface-variant/60">{t("test.idleHint")}</p>
          </div>
        )}

        {phase === "running" && (
          <div className="panel-elevated rounded-xl p-4 min-h-48">
            {runProgress ? (
              <RunProgressSteps progress={runProgress} />
            ) : (
              <div className="flex flex-col items-center justify-center h-40 gap-3">
                <Loader2 className="h-7 w-7 animate-spin text-accent-blue" />
                <p className="text-sm text-on-surface-variant">{t("test.progress.starting")}</p>
              </div>
            )}
          </div>
        )}

        {phase === "done" && result && (
          <div className="space-y-4">
            <div
              className={cn(
                "panel-elevated rounded-xl p-4 flex items-center gap-3",
                statusColor[result.status]
              )}
            >
              <StatusIcon className="h-5 w-5 shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold">{t(`test.status.${result.status}`)}</p>
                <p className="text-xs opacity-80 mt-0.5">
                  {result.summary.fieldsExtracted} {t("test.fieldsExtracted")} ·{" "}
                  {result.summary.passed}/{result.summary.total} {t("test.rulesPassed")}
                </p>
              </div>
              <Link href={`/audits/${result.id}`} className="shrink-0" target="_blank">
                <Button variant="outline" size="sm" className="gap-1.5 h-8 text-xs">
                  {t("test.viewReport")}
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </Link>
            </div>

            <TestRunSummaryDetails result={result} />

            <div className="panel-elevated rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 bg-surface-container-low border-b border-border">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  {t("test.ruleResults")}
                </p>
              </div>
              <div className="divide-y divide-border">
                {result.ruleResults.map((r) => {
                  const KindIcon = r.kind === "llm" ? Brain : Code;
                  const failedRule = isRuleFailure(r.status);
                  return (
                    <div key={r.id} className="flex items-start gap-3 px-4 py-3">
                      <RuleStatusIcon
                        status={r.status}
                        className={cn(
                          "h-4 w-4 shrink-0 mt-0.5",
                          ruleStatusColor(r.status)
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <KindIcon className="h-3 w-3 text-on-surface-variant" />
                          <span className="text-xs font-semibold text-on-surface">{r.name}</span>
                          {failedRule && r.severity === "reject" && (
                            <Badge variant="danger" className="text-[9px] px-1">
                              Reject
                            </Badge>
                          )}
                          {r.status !== "passed" && r.status !== "failed" && (
                            <Badge variant="secondary" className="text-[9px] px-1">
                              {ruleStatusLabel(r.status)}
                            </Badge>
                          )}
                        </div>
                        <p
                          className={cn(
                            "text-[11px] mt-0.5 leading-relaxed",
                            failedRule ? "text-danger-strong" : "text-on-surface-variant"
                          )}
                        >
                          {r.detail}
                        </p>
                      </div>
                    </div>
                  );
                })}
                {result.ruleResults.length === 0 && (
                  <p className="px-4 py-6 text-sm text-on-surface-variant text-center">
                    {t("test.noRules")}
                  </p>
                )}
              </div>
            </div>

            <Link href={`/audits/${result.id}`} target="_blank">
              <Button variant="outline" className="w-full gap-2 h-9">
                <FileText className="h-4 w-4" />
                {t("test.openFullReport")}
                <ArrowRight className="h-3.5 w-3.5 ml-auto" />
              </Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export function TestDeployStep({
  workflowId,
  name,
  apiKey,
  apiKeyHint,
  documents,
  rules,
  deployed,
  onDeploy,
  onBeforeRun,
  testSession,
  onTestSessionChange,
}: {
  workflowId: string;
  name: string;
  apiKey: string;
  apiKeyHint?: string;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  deployed: boolean;
  onDeploy: () => void;
  onBeforeRun?: () => Promise<string>;
  testSession: TestSessionState;
  onTestSessionChange: (patch: Partial<TestSessionState>) => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");

  return (
    <Tabs defaultValue="test" className="w-full">
      <TabsList className="mb-6 bg-surface-container-low/80 p-1 rounded-lg">
        <TabsTrigger value="test" className="gap-2">
          <FlaskConical className="h-3.5 w-3.5" />
          {t("test.tabLabel")}
        </TabsTrigger>
        <TabsTrigger value="deploy" className="gap-2">
          <Rocket className="h-3.5 w-3.5" />
          {t("deploy.tabLabel")}
          {deployed && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-success inline-block" />}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="test" forceMount className="data-[state=inactive]:hidden">
        <TestRunPanel
          workflowId={workflowId}
          documents={documents}
          rules={rules}
          workflowName={name}
          onBeforeRun={onBeforeRun}
          session={testSession}
          onSessionChange={onTestSessionChange}
          t={t}
        />
      </TabsContent>

      <TabsContent value="deploy">
        <div className="space-y-5">
          {!deployed ? (
            <div className="panel-elevated rounded-xl border-dashed p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-on-surface">{t("deploy.readyTitle")}</p>
                <p className="text-xs text-on-surface-variant mt-1">{t("deploy.readyHint")}</p>
              </div>
              <Button onClick={onDeploy} className="gap-2 shrink-0">
                <Rocket className="h-4 w-4" />
                {tCommon("deployWorkflow")}
              </Button>
            </div>
          ) : (
            <div className="panel-elevated rounded-xl border-success/30 bg-success/5 p-4 flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-success shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-success">{t("deploy.liveTitle")}</p>
                <p className="text-xs text-on-surface-variant mt-0.5">{t("deploy.liveHint")}</p>
              </div>
              <Button variant="outline" size="sm" onClick={onDeploy} className="gap-1.5 h-8 text-xs shrink-0">
                <Play className="h-3.5 w-3.5" />
                {tCommon("redeployWorkflow")}
              </Button>
            </div>
          )}

          {deployed && (
            <>
              <div>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant mb-3">
                  {t("deploy.apiTitle")}
                </h3>
                <ApiPanel
                  workflowId={workflowId}
                  workflowName={name}
                  apiKey={apiKey}
                  apiKeyHint={apiKeyHint}
                />
              </div>
              <p className="text-[11px] text-on-surface-variant">{t("deploy.liveSubmitHint")}</p>
            </>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
}
