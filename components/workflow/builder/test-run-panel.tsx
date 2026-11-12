"use client";

import { useMutation } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { Section } from "@/components/layout/page";
import { SectionHeading } from "@/components/layout/section-heading";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";
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
    <Section title={t("test.uploadTitle")} hint={t("test.uploadHint")}>
      <IngestionSection
        documents={documents}
        files={session.files}
        onFilesChange={(files) => onSessionChange({ ...session, files })}
      />
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => start.mutate()} disabled={busy}>
          <Play />
          {busy ? t("test.running") : t("test.runBtn")}
        </Button>
        {!hasFiles && !busy ? <p className="text-sm text-ink-3">{t("test.noFilesHint")}</p> : null}
      </div>
      {start.isError ? (
        <RunErrorAlert
          title={t("test.errorTitle")}
          message={errorMessage(start.error, t("test.errorTitle"))}
        />
      ) : null}
      {run.phase === "failed" ? (
        <RunErrorAlert title={t("test.errorTitle")} message={run.error} runId={session.runId} />
      ) : null}
      <div className="mt-2">
        <TestRunResults run={run} starting={start.isPending} />
      </div>
    </Section>
  );
}

/** Try the workflow on sample files, then publish it and call it from the API. */
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

  return (
    <div className="flex flex-col gap-12">
      <SectionHeading title={t("steps.upload")} description={t("steps.finalStepHint")} />
      <TestRunPanel
        documents={documents}
        rules={rules}
        session={testSession}
        onSessionChange={onTestSessionChange}
        saveForTestRun={saveForTestRun}
      />
      <Section
        title={t("deploy.tabLabel")}
        hint={deployed ? t("deploy.liveHint") : t("deploy.readyHint")}
      >
        {deployed ? (
          <>
            <p className="flex items-center gap-2 text-sm text-ink">
              <StatusGlyph status="live" />
              {t("deploy.liveTitle")}
            </p>
            <ApiPanel
              workflowId={workflowId}
              workflowName={name}
              apiKey={apiKey}
              apiKeyHint={apiKeyHint}
              documents={documents}
            />
          </>
        ) : (
          <Button onClick={onDeploy} disabled={sync !== "idle"} className="self-start">
            {sync === "deploying" ? tCommon("deploying") : tCommon("deployWorkflow")}
          </Button>
        )}
      </Section>
    </div>
  );
}
