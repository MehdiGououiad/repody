"use client";

import { useTranslations } from "next-intl";
import { CheckCircle2, Loader2, Play, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiPanel } from "@/components/workflow/api-panel";
import { IngestionSection } from "@/components/workflow/ingestion-section";
import { SectionHeading } from "@/components/layout/section-heading";
import { TestRunResults } from "@/components/workflow/builder/test-run-results";
import {
  formatUploadSize,
  type TestSessionState,
} from "@/components/workflow/builder/test-run-session";
import { syncRuleBodies } from "@/lib/rules/sync-rules";
import {
  runTestInline,
  runTestWithFiles,
  type ClientStepLabels,
  type RunProgress,
} from "@/lib/api/workflow-run";
import { buildClientProgress } from "@/lib/api/client-run-progress";
import { runErrorFromUnknown } from "@/lib/api/api-error";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { RunErrorAlert } from "@/components/workflow/run-error-alert";

export { emptyTestSession } from "@/components/workflow/builder/test-run-session";
export type { TestPhase, TestSessionState } from "@/components/workflow/builder/test-run-session";

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

function TestRunPanel({
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
  const { phase, progress, result, error, errorRunId, filesByDocId, uploadMeta } = session;
  const hasFiles = Object.keys(filesByDocId).length > 0;
  const stepLabels = clientStepLabels(t);

  const runTest = async () => {
    onSessionChange({
      phase: "running",
      progress: buildClientProgress(stepLabels, "save-workflow"),
      error: null,
      errorRunId: null,
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
    } catch (error) {
      const { message, runId } = runErrorFromUnknown(error);
      onSessionChange({
        error: message,
        errorRunId: runId ?? null,
        phase: "idle",
        progress: null,
      });
    }
  };

  return (
    <div className="space-y-8 min-w-0">
      <section className="space-y-4 min-w-0">
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
            const docIds = new Set(documents.map((document) => document.id));
            const nextMeta = { ...uploadMeta };

            for (const id of Object.keys(nextMeta)) {
              if (!docIds.has(id) || !(id in files)) delete nextMeta[id];
            }
            for (const [id, file] of Object.entries(files)) {
              nextMeta[id] = { name: file.name, size: formatUploadSize(file.size) };
            }

            onSessionChange({ filesByDocId: files, uploadMeta: nextMeta });
          }}
        />
        <Button
          className="w-full gap-2 sm:w-auto sm:min-w-[12rem]"
          onClick={runTest}
          disabled={phase === "running"}
        >
          {phase === "running" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {phase === "running" ? t("test.running") : t("test.runBtn")}
        </Button>
        {!hasFiles && phase === "idle" ? (
          <p className="text-[11px] text-on-surface-variant text-center sm:text-left">
            {t("test.noFilesHint")}
          </p>
        ) : null}
        {error ? (
          <RunErrorAlert title={t("test.errorTitle")} message={error} runId={errorRunId} />
        ) : null}
      </section>

      <TestRunResults phase={phase} progress={progress} result={result} />
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
    <div className="space-y-10 min-w-0">
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

      <div className="border-t border-border/80" role="separator" />

      <section className="space-y-5 min-w-0">
        <SectionHeading
          eyebrow="API"
          title={t("deploy.tabLabel")}
          description={t("deploy.sectionHint")}
        />

        {!deployed ? (
          <div className="panel-elevated rounded-xl border-dashed p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-on-surface">{t("deploy.readyTitle")}</p>
              <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">
                {t("deploy.readyHint")}
              </p>
            </div>
            <Button onClick={onDeploy} className="gap-2 shrink-0 w-full sm:w-auto">
              <Rocket className="h-4 w-4" />
              {tCommon("deployWorkflow")}
            </Button>
          </div>
        ) : (
          <>
            <div className="panel-elevated rounded-xl border-success/30 bg-success/5 p-4 flex flex-wrap items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-success shrink-0" />
              <div className="flex-1 min-w-[12rem]">
                <p className="text-sm font-semibold text-success">{t("deploy.liveTitle")}</p>
                <p className="text-xs text-on-surface-variant mt-0.5 leading-relaxed">
                  {t("deploy.liveHint")}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={onDeploy}
                className="gap-1.5 h-8 text-xs shrink-0 w-full sm:w-auto"
              >
                <Play className="h-3.5 w-3.5" />
                {tCommon("redeployWorkflow")}
              </Button>
            </div>

            <div className="min-w-0">
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant mb-3">
                {t("deploy.apiTitle")}
              </h3>
              <ApiPanel
                workflowId={workflowId}
                workflowName={name}
                apiKey={apiKey}
                apiKeyHint={apiKeyHint}
                documents={documents}
              />
            </div>
            <p className="text-[11px] text-on-surface-variant leading-relaxed">
              {t("deploy.liveSubmitHint")}
            </p>
          </>
        )}
      </section>
    </div>
  );
}
