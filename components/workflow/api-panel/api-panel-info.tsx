"use client";

import { Eye, EyeOff, Play, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { CopyButton } from "@/components/workflow/api-panel/api-panel-copy";
import { IngestionSection } from "@/components/workflow/ingestion-section";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import {
  buildWorkflowRunSnippets,
  runStateEndpoint,
  workflowDocumentSlots,
} from "@/lib/api/workflow-run-snippets";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import type { DocumentDef } from "@/lib/types";
import { cn } from "@/lib/utils";

function EndpointRow({ method, url }: { method: "POST" | "GET"; url: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-panel border border-line px-3 py-2">
      <span className="text-2xs font-semibold text-ink bg-accent/10 px-1.5 py-0.5 rounded font-mono shrink-0 w-10 text-center">
        {method}
      </span>
      <code translate="no" className="flex-1 text-2xs font-mono text-ink truncate">
        {url}
      </code>
      <CopyButton text={url} />
    </div>
  );
}

export function ApiInfoScreen({
  workflowId,
  workflowName,
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
  const [activeTab, setActiveTab] = useState<"curl" | "python" | "js">("curl");
  const mounted = useHydrated();

  const endpoint = mounted
    ? `${window.location.origin}/api/v1/workflows/${workflowId}/runs`
    : `/api/v1/workflows/${workflowId}/runs`;
  const hasFullKey = isFullWorkflowApiKey(apiKey);
  const maskedKey =
    apiKeyHint || (apiKey.length > 12 ? `${apiKey.slice(0, 12)}********` : apiKey || "\u2014");
  const displayKey = showKey && hasFullKey ? apiKey : maskedKey;
  const snippetKey = hasFullKey ? apiKey : maskedKey;
  const slots = workflowDocumentSlots(documents);
  const hasFiles = Object.keys(filesByDocId).length > 0;
  const canRun = hasFullKey && hasFiles;
  const snippets = buildWorkflowRunSnippets({
    endpoint,
    apiKey: snippetKey,
    documents,
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Badge variant="success" className="gap-1.5">
          <span className="size-1.5 rounded-full bg-pass animate-pulse" />
          {t("live")}
        </Badge>
        <span className="text-xs text-ink-3">{t("isDeployed", { name: workflowName })}</span>
      </div>

      <div className="rounded-xl overflow-hidden">
        <div className="px-4 py-2.5 border-b border-line flex items-center gap-2 bg-raised">
          <Zap className="h-3.5 w-3.5 text-ink" />
          <span className="text-2xs font-semibold text-ink-3">{t("endpointLabel")}</span>
        </div>
        <div className="p-4 space-y-2.5">
          <EndpointRow method="POST" url={endpoint} />
          <EndpointRow method="GET" url={runStateEndpoint(endpoint)} />
          <p className="text-2xs text-ink-3 leading-relaxed">{t("pollHint")}</p>
          <div className="flex items-center gap-2 rounded-lg bg-panel border border-line px-3 py-2">
            <span className="text-2xs font-semibold text-ink-3 shrink-0">{t("keyLabel")}</span>
            <code translate="no" className="flex-1 text-2xs font-mono text-ink truncate">
              {displayKey}
            </code>
            <button
              type="button"
              onClick={() => setShowKey((value) => !value)}
              aria-label={showKey ? t("hideKey") : t("showKey")}
              className="text-ink-3 hover:text-ink transition-colors shrink-0"
            >
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
            <CopyButton text={hasFullKey ? apiKey : maskedKey} />
          </div>
        </div>
      </div>

      {slots.length > 0 ? (
        <div className="rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 border-b border-line bg-raised">
            <span className="text-2xs font-semibold text-ink-3">{t("documentSlotsLabel")}</span>
          </div>
          <div className="p-4 space-y-2">
            <p className="text-xs text-ink-3 leading-relaxed">{t("schemaHint")}</p>
            <ul className="space-y-2">
              {slots.map((doc, index) => {
                const fieldCount = doc.schema.filter((field) => field.name.trim()).length;

                return (
                  <li
                    key={doc.id}
                    className="rounded-lg border border-line bg-panel px-3 py-2 text-xs"
                  >
                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                      <span className="font-mono text-2xs text-ink-3 shrink-0">{index + 1}.</span>
                      <span className="font-semibold text-ink truncate">
                        {doc.documentType.trim()}
                      </span>
                      <span className="text-ink-3">{t("fieldsCount", { count: fieldCount })}</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      ) : null}

      <div className="rounded-xl overflow-hidden">
        <div
          className="flex items-center border-b border-line"
          role="tablist"
          aria-label={t("endpointLabel")}
        >
          {(["curl", "python", "js"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 text-xs font-medium transition-colors  ",
                activeTab === tab
                  ? "border-b-2 border-accent text-ink"
                  : "text-ink-3 hover:text-ink"
              )}
            >
              {tab}
            </button>
          ))}
          <div className="flex-1" />
          <CopyButton text={snippets[activeTab]} className="mr-4" />
        </div>
        <pre className="p-4 text-2xs font-mono text-ink overflow-x-auto leading-relaxed bg-panel whitespace-pre-wrap break-all">
          <code translate="no">{snippets[activeTab]}</code>
        </pre>
      </div>

      <div className="rounded-xl p-4 space-y-3 min-w-0">
        <div>
          <Label className="text-xs font-semibold text-ink-3">
            {slots.length > 1 ? t("testDocumentsLabel") : t("testDocumentLabel")}
          </Label>
          <p className="text-2xs text-ink-3 mt-1 leading-relaxed">{t("testUploadHint")}</p>
        </div>
        <IngestionSection
          documents={documents}
          rules={[]}
          files={filesByDocId}
          onFilesChange={onFilesChange}
        />
        {!hasFiles ? <p className="text-2xs text-warn-ink">{t("testUploadRequired")}</p> : null}
        {!hasFullKey ? <p className="text-2xs text-warn-ink">{t("keyUnavailable")}</p> : null}
      </div>
      <button
        type="button"
        onClick={onRun}
        disabled={!canRun}
        className="group flex items-center justify-between w-full rounded-xl border-2 border-dashed border-accent/40 bg-accent/5 hover:bg-accent/10 hover:border-accent/70 transition-[border-color,background-color] px-5 py-4 disabled:opacity-50 disabled:pointer-events-none"
      >
        <div className="text-left">
          <p className="text-sm font-semibold text-ink">{t("runTest")}</p>
          <p className="text-xs text-ink-3 mt-0.5">{t("runTestHint")}</p>
        </div>
        <div className="size-9 rounded-full bg-accent/15 group-hover:bg-accent/25 flex items-center justify-center transition-colors shrink-0 ml-4">
          <Play className="h-4 w-4 text-ink" />
        </div>
      </button>
    </div>
  );
}
