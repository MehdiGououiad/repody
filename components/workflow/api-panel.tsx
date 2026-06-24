"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ApiInfoScreen } from "@/components/workflow/api-panel-info";
import { ApiRunLoadingScreen } from "@/components/workflow/api-panel-loading";
import { ApiRunReportScreen, type ApiRunReport } from "@/components/workflow/api-panel-report";
import { RunErrorAlert } from "@/components/workflow/run-error-alert";
import { runErrorFromUnknown } from "@/lib/api/api-error";
import { runWorkflowApi, type RunProgress } from "@/lib/api/workflow-run";
import { reportClientError } from "@/lib/report-error";
import type { DocumentDef } from "@/lib/types";

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
  const t = useTranslations("workflows.builder");
  const [screen, setScreen] = useState<Screen>("info");
  const [report, setReport] = useState<ApiRunReport | null>(null);
  const [filesByDocId, setFilesByDocId] = useState<Record<string, File>>({});
  const [runProgress, setRunProgress] = useState<RunProgress | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [runErrorRunId, setRunErrorRunId] = useState<string | null>(null);

  const run = async () => {
    if (Object.keys(filesByDocId).length === 0) return;
    setScreen("loading");
    setRunProgress(null);
    setRunError(null);
    setRunErrorRunId(null);
    try {
      const detail = await runWorkflowApi(
        workflowId,
        apiKey,
        { documents, filesByDocId },
        (progress) => setRunProgress(progress)
      );
      setReport({ ...detail, processedAt: detail.createdAt });
      setScreen("report");
    } catch (error) {
      reportClientError(error, { workflowId, surface: "api-panel" });
      const { message, runId } = runErrorFromUnknown(error);
      setRunError(message);
      setRunErrorRunId(runId ?? null);
      setScreen("info");
    }
  };

  if (screen === "loading") {
    return <ApiRunLoadingScreen workflowName={workflowName} progress={runProgress} />;
  }

  if (screen === "report" && report) {
    return <ApiRunReportScreen report={report} onBack={() => setScreen("info")} />;
  }

  return (
    <>
      {runError ? (
        <div className="mb-4">
          <RunErrorAlert
            title={t("test.errorTitle")}
            message={runError}
            runId={runErrorRunId}
          />
        </div>
      ) : null}
      <ApiInfoScreen
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
