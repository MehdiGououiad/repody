"use client";

import { useTranslations } from "next-intl";
import { DocumentMarkdownPreview } from "@/components/documents/document-markdown-preview";
import { CopyableOutputPanel, OutputPre } from "@/components/shared/copyable-output-panel";

export function DocumentMarkdownPanel({ text, className }: { text: string; className?: string }) {
  const t = useTranslations("workflows.builder.documentMarkdown");
  const normalized = text.trim();
  const lineCount = normalized.split("\n").length;
  const hasTables = /\|.+\|/.test(normalized);

  const subtitle = [
    t("subtitle", { lines: lineCount, chars: normalized.length }),
    hasTables ? t("hasTables") : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <CopyableOutputPanel
      className={className}
      labels={{
        title: t("title"),
        subtitle,
        copy: t("copy"),
        copied: t("copied"),
        copyFailed: t("copyFailed"),
        previewTab: t("previewTab"),
        sourceTab: t("sourceTab"),
      }}
      copyText={normalized}
      preview={
        <div className="p-4 max-h-[520px] overflow-y-auto">
          <DocumentMarkdownPreview text={normalized} />
        </div>
      }
      source={<OutputPre muted>{normalized}</OutputPre>}
    />
  );
}
