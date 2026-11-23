"use client";

import { useShortcut, useShortcutHint } from "@ui-sdk/react/shortcuts";
import { Play, ScanSearch } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { Gate } from "@/components/auth/gate";
import { Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { ApiPanel } from "@/components/workflow/api-panel/api-panel";
import { TestRunResults } from "@/components/workflow/builder/test-run-results";
import type { BuilderSync } from "@/components/workflow/builder/use-builder-workflow";
import type { TestRun } from "@/components/workflow/builder/use-test-run";
import { IngestionSection } from "@/components/workflow/ingestion-section";
import { RunErrorAlert } from "@/components/workflow/run-error-alert";
import { wakeModel } from "@/lib/api/runs";
import { errorMessage } from "@/lib/query/get-query-client";
import type { DocumentDef } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";

export function TestDeployStep({
  workflowId,
  name,
  apiKey,
  apiKeyHint,
  documents,
  deployed,
  sync,
  test,
  onDeploy,
}: {
  workflowId: string;
  name: string;
  apiKey: string;
  apiKeyHint?: string;
  documents: DocumentDef[];
  deployed: boolean;
  sync: BuilderSync;
  test: TestRun;
  onDeploy: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const extractHint = useShortcutHint("mod+enter");

  useShortcut("mod+enter", test.start, {
    allowInInput: true,
    when: () => test.ready,
    description: t("test.extractAndValidate"),
  });

  // Pre-warm the GPU only here, where a test is about to run: it costs GPU time until it stops.
  useEffect(() => {
    if (test.canRun && test.sampleCount > 0) wakeModel();
  }, [test.canRun, test.sampleCount]);

  const handleFilesChange = (nextFiles: Record<string, File>) => {
    const added = Object.entries(nextFiles).some(([id, file]) => test.files[id] !== file);
    test.setFiles(nextFiles);
    if (added && test.canRun) wakeModel();
  };

  const hasPassingTest = test.run.phase === "done" && test.run.result.status === "passed";
  const hasNonPassingTest = test.run.phase === "done" && test.run.result.status !== "passed";

  return (
    <div className="grid grid-cols-1 items-start gap-8 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-6">
        <Section title={t("test.sectionTitle")} hint={t("test.sectionHint")}>
          <IngestionSection
            documents={documents}
            files={test.files}
            onFilesChange={handleFilesChange}
          />
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Gate permission="run:execute">
              <Button
                variant="primary"
                size="md"
                onClick={test.start}
                disabled={!test.ready}
                title={test.sampleCount === 0 ? t("test.needSample") : undefined}
              >
                <Play />
                {test.busy ? t("test.running") : t("test.extractAndValidate")}
                {test.busy ? (
                  <span className="tabular-nums opacity-80">
                    {formatDurationMs(test.elapsedMs)}
                  </span>
                ) : (
                  <Kbd className="ms-0.5">{extractHint.text}</Kbd>
                )}
              </Button>
            </Gate>
            {test.sampleCount === 0 ? (
              <p className="text-xs text-ink-3">{t("test.needSample")}</p>
            ) : null}
          </div>
        </Section>

        {test.startError ? (
          <RunErrorAlert
            title={t("test.errorTitle")}
            message={errorMessage(test.startError, t("test.errorTitle"))}
          />
        ) : null}
        {test.run.phase === "failed" ? (
          <RunErrorAlert title={t("test.errorTitle")} message={test.run.error} runId={test.runId} />
        ) : null}

        {test.run.phase === "idle" && !test.starting ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line-strong px-6 py-12 text-center">
            <span className="flex size-10 items-center justify-center rounded-full bg-accent-wash text-accent-ink">
              <ScanSearch className="size-5" aria-hidden />
            </span>
            <p className="text-[13px] font-medium text-ink">{t("test.emptyTitle")}</p>
            <p className="max-w-sm text-xs text-ink-3">{t("test.emptyHint")}</p>
          </div>
        ) : (
          <TestRunResults run={test.run} starting={test.starting} elapsedMs={test.elapsedMs} />
        )}
      </div>

      <section className="flex flex-col gap-4 rounded-xl bg-panel p-5 shadow-panel">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="eyebrow text-ink-2">{t("deploy.tabLabel")}</h2>
            <p className="mt-1 text-xs text-ink-3">
              {deployed ? t("deploy.liveHint") : t("deploy.readyHint")}
            </p>
          </div>
          <span
            className={cn(
              "inline-flex h-5 shrink-0 items-center gap-1.5 rounded-full px-2 text-xs font-medium",
              deployed ? "bg-pass-wash text-pass-ink" : "bg-selected text-ink-3"
            )}
          >
            <StatusGlyph status={deployed ? "live" : "draft"} className="size-3" />
            {deployed ? t("deploy.liveTitle") : t("statusDraft")}
          </span>
        </div>

        {!hasPassingTest ? (
          <div
            role="status"
            className="flex items-start gap-2.5 rounded-lg bg-warn-wash/70 px-3 py-2.5 text-xs text-warn-ink"
          >
            <StatusGlyph status="warning" className="mt-0.5 size-3.5" />
            <p>
              {hasNonPassingTest ? t("deploy.testNotPassedWarning") : t("deploy.untestedWarning")}
            </p>
          </div>
        ) : null}

        <Gate permission="workflow:deploy">
          <Button
            variant={!deployed && hasPassingTest ? "primary" : "secondary"}
            className="self-start"
            onClick={onDeploy}
            disabled={sync !== "idle"}
          >
            {sync === "deploying"
              ? tCommon("deploying")
              : deployed
                ? tCommon("redeployWorkflow")
                : tCommon("deployWorkflow")}
          </Button>
        </Gate>

        {deployed ? (
          <div className="border-t border-line pt-4">
            <ApiPanel
              workflowId={workflowId}
              workflowName={name}
              apiKey={apiKey}
              apiKeyHint={apiKeyHint}
              documents={documents}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
