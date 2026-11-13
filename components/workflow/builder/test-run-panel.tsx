"use client";

import { useTranslations } from "next-intl";
import { Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { ApiPanel } from "@/components/workflow/api-panel/api-panel";
import { TestRunResults } from "@/components/workflow/builder/test-run-results";
import type { BuilderSync } from "@/components/workflow/builder/use-builder-workflow";
import type { RunView } from "@/lib/api/runs";
import type { DocumentDef } from "@/lib/types";

/** Publish: the key and the code to call the workflow, and the last extraction as a full report. */
export function PublishStep({
  workflowId,
  name,
  apiKey,
  apiKeyHint,
  documents,
  deployed,
  sync,
  run,
  onDeploy,
}: {
  workflowId: string;
  name: string;
  apiKey: string;
  apiKeyHint?: string;
  documents: DocumentDef[];
  deployed: boolean;
  sync: BuilderSync;
  run: RunView;
  onDeploy: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");

  return (
    <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Section
        title={t("deploy.tabLabel")}
        hint={deployed ? t("deploy.liveHint") : t("deploy.readyHint")}
      >
        {deployed ? (
          <>
            <p className="flex items-center gap-2 text-[13px] font-medium text-pass-ink">
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
          <Button
            variant="primary"
            className="self-start"
            onClick={onDeploy}
            disabled={sync !== "idle"}
          >
            {sync === "deploying" ? tCommon("deploying") : tCommon("deployWorkflow")}
          </Button>
        )}
      </Section>
      <Section title={t("publish.lastExtraction")}>
        {run.phase === "idle" ? (
          <p className="rounded-lg bg-raised px-4 py-6 text-[13px] text-ink-3 shadow-[0_0_0_1px_var(--line)]">
            {t("publish.noExtraction")}
          </p>
        ) : (
          <TestRunResults run={run} starting={false} />
        )}
      </Section>
    </div>
  );
}
