"use client";

import { Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import type { RunProgress } from "@/lib/api/workflow-run";

export function ApiRunLoadingScreen({
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
        <p className="text-xs text-on-surface-variant mt-1">
          {t("processingHint", { name: workflowName })}
        </p>
      </div>
      {progress ? (
        <div className="w-full max-w-md text-left">
          <RunProgressSteps progress={progress} />
        </div>
      ) : (
        <p className="text-xs text-on-surface-variant">{t("parseStep")}\u2026</p>
      )}
    </div>
  );
}
