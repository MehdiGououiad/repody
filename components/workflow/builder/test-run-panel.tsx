"use client";

import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Play, Rocket } from "lucide-react";
import { useTranslations } from "next-intl";
import { SectionHeading } from "@/components/layout/section-heading";
import { Button } from "@/components/ui/button";
import { ApiPanel } from "@/components/workflow/api-panel/api-panel";
import { TestRunResults } from "@/components/workflow/builder/test-run-results";
import type { BuilderSync, TestSession } from "@/components/workflow/builder/use-builder-workflow";
import { IngestionSection } from "@/components/workflow/ingestion-section";
import { RunErrorAlert } from "@/components/workflow/run-error-alert";
import { startRun, useRun } from "@/lib/api/runs";
import { errorMessage } from "@/lib/query/get-query-client";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

function TestRunPanel({
  documents,
  rules,
  session,
  onSessionChange,
  saveForTestRun,
}: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  session: TestSession;
  onSessionChange: (session: TestSession) => void;
  saveForTestRun: () => Promise<string>;
}) {
  const t = useTranslations("workflows.builder");
  // Save first, so the run is what the builder shows; without files the rules run on the
  // schema's placeholder values. A failed save or start shows in the same alert.
  const start = useMutation({
    mutationFn: async () =>
      startRun({ workflowId: await saveForTestRun(), documents, rules, files: session.files }),
    onMutate: () => onSessionChange({ ...session, runId: null }),
    onSuccess: ({ runId }) => onSessionChange({ ...session, runId }),
  });
  const run = useRun(session.runId);
  const busy = start.isPending || run.phase === "running";
  const hasFiles = Object.keys(session.files).length > 0;

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
          files={session.files}
          onFilesChange={(files) => onSessionChange({ ...session, files })}
        />
        <Button
          className="w-full gap-2 sm:w-auto sm:min-w-[12rem]"
          onClick={() => start.mutate()}
          disabled={busy}
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {busy ? t("test.running") : t("test.runBtn")}
        </Button>
        {!hasFiles && !busy ? (
          <p className="text-[11px] text-on-surface-variant text-center sm:text-left">
            {t("test.noFilesHint")}
          </p>
        ) : null}
        {start.isError ? (
          <RunErrorAlert
            title={t("test.errorTitle")}
            message={errorMessage(start.error, t("test.errorTitle"))}
          />
        ) : null}
        {run.phase === "failed" ? (
          <RunErrorAlert title={t("test.errorTitle")} message={run.error} runId={session.runId} />
        ) : null}
      </section>

      <TestRunResults run={run} starting={start.isPending} />
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
  sync,
  onDeploy,
  saveForTestRun,
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
  sync: BuilderSync;
  onDeploy: () => void;
  saveForTestRun: () => Promise<string>;
  testSession: TestSession;
  onTestSessionChange: (session: TestSession) => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const deployLabel =
    sync === "deploying"
      ? tCommon("deploying")
      : deployed
        ? tCommon("redeployWorkflow")
        : tCommon("deployWorkflow");

  return (
    <div className="space-y-10 min-w-0">
      <TestRunPanel
        documents={documents}
        rules={rules}
        session={testSession}
        onSessionChange={onTestSessionChange}
        saveForTestRun={saveForTestRun}
      />

      <hr className="border-border/80" />

      <section className="space-y-5 min-w-0">
        <SectionHeading
          eyebrow={t("deploy.eyebrow")}
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
            <Button
              onClick={onDeploy}
              disabled={sync !== "idle"}
              className="gap-2 shrink-0 w-full sm:w-auto"
            >
              <Rocket className="h-4 w-4" />
              {deployLabel}
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
                disabled={sync !== "idle"}
                className="gap-1.5 h-8 text-xs shrink-0 w-full sm:w-auto"
              >
                <Play className="h-3.5 w-3.5" />
                {deployLabel}
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
