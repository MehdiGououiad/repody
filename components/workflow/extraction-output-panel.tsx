"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { CopyableOutputPanel, OutputPre } from "@/components/shared/copyable-output-panel";
import { DocumentMarkdownPanel } from "@/components/workflow/document-markdown-panel";
import type { RunDocumentExtractionMeta } from "@/lib/types";

function formatJson(text: string): string {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
    return trimmed;
  }
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2);
  } catch {
    return trimmed;
  }
}

function ExtractionJsonPanel({ text, className }: { text: string; className?: string }) {
  const t = useTranslations("workflows.builder.jsonOutput");
  const formatted = useMemo(() => formatJson(text), [text]);

  return (
    <CopyableOutputPanel
      className={className}
      labels={{
        title: t("title"),
        subtitle: t("subtitle", {
          lines: formatted.split("\n").length,
          chars: formatted.length,
        }),
        copy: t("copy"),
        copied: t("copied"),
        copyFailed: t("copyFailed"),
        previewTab: t("previewTab"),
        sourceTab: t("sourceTab"),
      }}
      copyText={formatted}
      preview={<OutputPre>{formatted}</OutputPre>}
      source={<OutputPre muted>{text.trim()}</OutputPre>}
    />
  );
}
export function DocumentExtractionOutput({
  extraction,
  className,
}: {
  extraction: RunDocumentExtractionMeta;
  className?: string;
}) {
  if (extraction.markdownText) {
    return <DocumentMarkdownPanel text={extraction.markdownText} className={className} />;
  }

  if (extraction.rawText) {
    return <ExtractionJsonPanel text={extraction.rawText} className={className} />;
  }

  return null;
}
