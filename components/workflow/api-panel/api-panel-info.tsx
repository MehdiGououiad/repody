"use client";

import { Eye, EyeOff, Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import { CopyButton } from "@/components/workflow/api-panel/api-panel-copy";
import { IngestionSection } from "@/components/workflow/ingestion-section";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import { buildWorkflowRunSnippets, runStateEndpoint } from "@/lib/api/workflow-run-snippets";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import type { DocumentDef } from "@/lib/types";

const FRAME = "overflow-hidden rounded-lg shadow-panel";

function Row({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex min-h-10 items-center gap-3 px-3 py-1">
      <span className="w-12 shrink-0 font-mono text-xs font-semibold text-ink-3">{label}</span>
      {children}
    </div>
  );
}

/** How to call the published workflow: endpoints, key, examples, and a run from here. */
export function ApiInfoScreen({
  workflowId,
  apiKey,
  apiKeyHint,
  documents,
  onRun,
  filesByDocId,
  onFilesChange,
}: {
  workflowId: string;
  workflowName: string;
  apiKey: string;
  apiKeyHint?: string;
  documents: DocumentDef[];
  onRun: () => void;
  filesByDocId: Record<string, File>;
  onFilesChange: (files: Record<string, File>) => void;
}) {
  const t = useTranslations("workflows.builder.api");
  const [showKey, setShowKey] = useState(false);
  const mounted = useHydrated();
  const endpoint = mounted
    ? `${window.location.origin}/api/v1/workflows/${workflowId}/runs`
    : `/api/v1/workflows/${workflowId}/runs`;
  const hasFullKey = isFullWorkflowApiKey(apiKey);
  const maskedKey =
    apiKeyHint || (apiKey.length > 12 ? `${apiKey.slice(0, 12)}••••••••` : apiKey || "—");
  const snippets = buildWorkflowRunSnippets({
    endpoint,
    apiKey: hasFullKey ? apiKey : maskedKey,
    documents,
  });
  const hasFiles = Object.keys(filesByDocId).length > 0;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <div className={`${FRAME} divide-y divide-line`}>
          <Row label="POST">
            <code translate="no" className="min-w-0 flex-1 truncate font-mono text-xs text-ink">
              {endpoint}
            </code>
            <CopyButton text={endpoint} />
          </Row>
          <Row label="GET">
            <code translate="no" className="min-w-0 flex-1 truncate font-mono text-xs text-ink">
              {runStateEndpoint(endpoint)}
            </code>
            <CopyButton text={runStateEndpoint(endpoint)} />
          </Row>
          <Row label={t("keyLabel")}>
            <code translate="no" className="min-w-0 flex-1 truncate font-mono text-xs text-ink">
              {showKey && hasFullKey ? apiKey : maskedKey}
            </code>
            {hasFullKey ? (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setShowKey((v) => !v)}
                aria-label={showKey ? t("hideKey") : t("showKey")}
              >
                {showKey ? <EyeOff /> : <Eye />}
              </Button>
            ) : null}
            <CopyButton text={hasFullKey ? apiKey : maskedKey} />
          </Row>
        </div>
        <p className="text-sm text-ink-3">{t("pollHint")}</p>
        {!hasFullKey ? <p className="text-sm text-warn-ink">{t("keyUnavailable")}</p> : null}
      </div>

      <Tabs defaultValue="curl" className={FRAME}>
        <div className="flex h-9 items-center border-b border-line ps-1.5 pe-1">
          <TabsList aria-label="Code">
            {(["curl", "python", "js"] as const).map((tab) => (
              <TabsTab key={tab} value={tab} className="h-6 px-2 text-xs">
                {t(`lang.${tab}`)}
              </TabsTab>
            ))}
          </TabsList>
        </div>
        {(["curl", "python", "js"] as const).map((tab) => (
          <TabsPanel key={tab} value={tab} className="relative">
            <pre className="max-h-96 overflow-auto overscroll-contain bg-field p-4 pe-12 font-mono text-xs leading-relaxed text-ink-2">
              <code translate="no">{snippets[tab]}</code>
            </pre>
            <CopyButton text={snippets[tab]} className="absolute end-2 top-2" />
          </TabsPanel>
        ))}
      </Tabs>

      <div className="flex flex-col gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{t("runTest")}</h3>
          <p className="mt-0.5 text-sm text-ink-3">{t("runTestHint")}</p>
        </div>
        <IngestionSection
          documents={documents}
          files={filesByDocId}
          onFilesChange={onFilesChange}
        />
        <Button
          variant="secondary"
          onClick={onRun}
          disabled={!hasFullKey || !hasFiles}
          className="self-start"
          title={!hasFiles ? t("testUploadRequired") : undefined}
        >
          <Play />
          {t("runWithKey")}
        </Button>
      </div>
    </div>
  );
}
