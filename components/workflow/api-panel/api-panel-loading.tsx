"use client";

import { useTranslations } from "next-intl";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import type { RunProgress } from "@/lib/types";

/** A run started with the API key, while it runs: its live timeline. */
export function ApiRunLoadingScreen({
  workflowName,
  progress,
}: {
  workflowName: string;
  progress: RunProgress | null;
}) {
  const t = useTranslations("workflows.builder.api");
  return (
    <div className="flex max-w-md flex-col gap-4" aria-live="polite">
      <p className="text-sm text-ink-3">{t("processingHint", { name: workflowName })}</p>
      {progress ? (
        <RunProgressSteps progress={progress} />
      ) : (
        <p className="text-sm text-ink-3">{t("parseStep")}…</p>
      )}
    </div>
  );
}
