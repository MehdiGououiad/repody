"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { ApiInfoScreen } from "@/components/workflow/api-panel/api-panel-info";
import { ApiRunLoadingScreen } from "@/components/workflow/api-panel/api-panel-loading";
import { ApiRunReportScreen } from "@/components/workflow/api-panel/api-panel-report";
import { RunErrorAlert } from "@/components/workflow/run-error-alert";
import { useRun, useStartRun } from "@/lib/api/runs";
import { errorMessage } from "@/lib/query/get-query-client";
import type { DocumentDef } from "@/lib/types";

/** Try the deployed workflow as an integrator would: a run started with its API key. */
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
  const [files, setFiles] = useState<Record<string, File>>({});
  const [runId, setRunId] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(true);
  const start = useStartRun();
  const run = useRun(runId);

  const startRun = () => {
    setRunId(null);
    setShowReport(true);
    start.mutate(
      { workflowId, documents, files, apiKey },
      { onSuccess: ({ runId: id }) => setRunId(id) },
    );
  };

  if (start.isPending || run.phase === "running") {
    return (
      <ApiRunLoadingScreen
        workflowName={workflowName}
        progress={run.phase === "running" ? run.progress : null}
      />
    );
  }
  if (run.phase === "done" && showReport) {
    return <ApiRunReportScreen report={run.result} onBack={() => setShowReport(false)} />;
  }

  const error = start.isError
    ? errorMessage(start.error, t("test.errorTitle"))
    : run.phase === "failed"
      ? run.error
      : null;
  return (
    <>
      {error ? (
        <div className="mb-4">
          <RunErrorAlert title={t("test.errorTitle")} message={error} runId={runId} />
        </div>
      ) : null}
      <ApiInfoScreen
        workflowId={workflowId}
        workflowName={workflowName}
        apiKey={apiKey}
        apiKeyHint={apiKeyHint}
        documents={documents}
        onRun={startRun}
        filesByDocId={files}
        onFilesChange={setFiles}
      />
    </>
  );
}
