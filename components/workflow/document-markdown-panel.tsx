"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, Copy, FileText, ScanText } from "lucide-react";
import { toast } from "sonner";

import { DocumentMarkdownPreview } from "@/components/documents/document-markdown-preview";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
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
  const [copied, setCopied] = useState(false);
  const normalized = useMemo(() => normalizeDocumentMarkdown(text), [text]);
  const charCount = normalized.length;
  const lineCount = normalized.split("\n").length;
  const pageCount = (normalized.match(/^## Page \d+$/gm) ?? []).length;
  const hasTables = /\|.+\|/.test(normalized);
  const isDocumentModel = readPathUsed === "document_model";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(normalized);
      setCopied(true);
      toast.success(t("copied"));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("copyFailed"));
    }
  };

  return (
    <div className={cn("panel-elevated rounded-xl overflow-hidden", className)}>
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-gradient-to-r from-accent-blue/5 to-transparent">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="size-8 rounded-lg bg-accent-blue/10 flex items-center justify-center shrink-0">
            {isDocumentModel ? (
              <ScanText className="h-4 w-4 text-accent-blue" />
            ) : (
              <FileText className="h-4 w-4 text-accent-blue" />
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-on-surface">{t("title")}</p>
            <p className="text-[11px] text-on-surface-variant truncate">
              {t("subtitle", { lines: lineCount, chars: charCount.toLocaleString() })}
              {pageCount > 0 ? ` · ${pageCount} page${pageCount === 1 ? "" : "s"}` : ""}
              {hasTables ? ` · ${t("hasTables")}` : ""}
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0 h-8"
          onClick={handleCopy}
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? t("copied") : t("copy")}
        </Button>
      </div>

      <Tabs defaultValue="preview" className="w-full">
        <div className="px-4 pt-2 border-b border-border bg-surface-container-lowest">
          <TabsList className="h-8 bg-transparent p-0 gap-4">
            <TabsTrigger
              value="preview"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-0 pb-2 text-xs"
            >
              {t("previewTab")}
            </TabsTrigger>
            <TabsTrigger
              value="source"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-0 pb-2 text-xs"
            >
              {t("sourceTab")}
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="preview" className="mt-0 p-4 max-h-[520px] overflow-y-auto">
          <DocumentMarkdownPreview text={normalized} />
        </TabsContent>
        <TabsContent value="source" className="mt-0 p-0">
          <pre className="max-h-[520px] overflow-auto p-4 text-[11px] leading-relaxed font-mono text-on-surface-variant bg-surface-container-lowest whitespace-pre-wrap break-words">
            {normalized}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}
