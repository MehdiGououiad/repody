"use client";

import { FileText, ScanText } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { DocumentMarkdownPreview } from "@/components/documents/document-markdown-preview";
import { CopyableOutputPanel, OutputPre } from "@/components/shared/copyable-output-panel";
import { normalizeDocumentMarkdown } from "@/lib/document-markdown/normalize";

export function DocumentMarkdownPanel({
  text,
  readPathUsed,
  className,
}: {
  text: string;
  readPathUsed?: string;
  className?: string;
}) {
  const t = useTranslations("workflows.builder.documentMarkdown");
  const normalized = useMemo(() => normalizeDocumentMarkdown(text), [text]);
  const lineCount = normalized.split("\n").length;
  const pageCount = (normalized.match(/^## Page \d+$/gm) ?? []).length;
  const hasTables = /\|.+\|/.test(normalized);
  const Icon = readPathUsed === "document_model" ? ScanText : FileText;

  const subtitle = [
    t("subtitle", { lines: lineCount, chars: normalized.length.toLocaleString() }),
    pageCount > 0 ? `${pageCount} page${pageCount === 1 ? "" : "s"}` : null,
    hasTables ? t("hasTables") : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <CopyableOutputPanel
      className={className}
      headerClassName="from-accent-blue/5"
      icon={
        <div className="size-8 rounded-lg bg-accent-blue/10 flex items-center justify-center shrink-0">
          <Icon className="h-4 w-4 text-accent-blue" />
        </div>
      }
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
