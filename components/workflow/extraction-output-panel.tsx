"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Braces, Check, Copy } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import type { RunDocumentExtractionMeta } from "@/lib/types/audit";
import { OcrMarkdownPanel } from "@/components/workflow/ocr-markdown-panel";

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
  const [copied, setCopied] = useState(false);
  const formatted = useMemo(() => formatJson(text), [text]);
  const lineCount = formatted.split("\n").length;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatted);
      setCopied(true);
      toast.success(t("copied"));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("copyFailed"));
    }
  };

  return (
    <div className={cn("panel-elevated rounded-xl overflow-hidden", className)}>
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Braces className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-on-surface">{t("title")}</p>
            <p className="text-[11px] text-on-surface-variant truncate">
              {t("subtitle", { lines: lineCount, chars: formatted.length.toLocaleString() })}
            </p>
          </div>
        </div>
        <Button type="button" variant="outline" size="sm" className="shrink-0 h-8" onClick={handleCopy}>
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
        <TabsContent value="preview" className="mt-0 p-0">
          <pre className="max-h-[520px] overflow-auto p-4 text-[11px] leading-relaxed font-mono text-on-surface bg-surface-container-lowest whitespace-pre-wrap break-words">
            {formatted}
          </pre>
        </TabsContent>
        <TabsContent value="source" className="mt-0 p-0">
          <pre className="max-h-[520px] overflow-auto p-4 text-[11px] leading-relaxed font-mono text-on-surface-variant bg-surface-container-lowest whitespace-pre-wrap break-words">
            {text.trim()}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export function DocumentExtractionOutput({
  extraction,
  className,
}: {
  extraction: RunDocumentExtractionMeta;
  className?: string;
}) {
  if (extraction.markdownExtraction && extraction.ocrText) {
    return (
      <OcrMarkdownPanel
        text={extraction.ocrText}
        readPathUsed={extraction.readPathUsed}
        className={className}
      />
    );
  }

  if (extraction.rawText) {
    return <ExtractionJsonPanel text={extraction.rawText} className={className} />;
  }

  return null;
}
