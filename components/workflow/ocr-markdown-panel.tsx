"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, Copy, FileText, ScanText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { normalizeOcrMarkdown } from "@/lib/ocr-markdown/normalize";

function MarkdownPreview({ text }: { text: string }) {
  return (
    <article className="space-y-2 text-sm text-on-surface-variant leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h2 className="text-lg font-bold text-on-surface mt-5 mb-2">{children}</h2>
          ),
          h2: ({ children }) => (
            <h3 className="text-base font-semibold text-on-surface mt-5 mb-2 pb-1 border-b border-border/60">
              {children}
            </h3>
          ),
          h3: ({ children }) => (
            <h4 className="text-sm font-semibold text-on-surface mt-4 mb-1.5 pl-2 border-l-2 border-primary/40">
              {children}
            </h4>
          ),
          p: ({ children }) => <p className="text-sm text-on-surface-variant">{children}</p>,
          li: ({ children }) => (
            <li className="ml-4 list-disc marker:text-primary">{children}</li>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-xl border border-border my-4 shadow-sm bg-card">
              <table className="w-full text-xs border-collapse min-w-[320px]">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gradient-to-r from-accent-blue/10 to-surface-container-low">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2.5 text-left font-semibold text-on-surface whitespace-nowrap border-b border-border">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-on-surface-variant align-top border-b border-border/60">
              {children}
            </td>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </article>
  );
}

export function OcrMarkdownPanel({
  text,
  readPathUsed,
  className,
}: {
  text: string;
  readPathUsed?: string;
  className?: string;
}) {
  const t = useTranslations("workflows.builder.ocrOutput");
  const [copied, setCopied] = useState(false);
  const normalized = useMemo(() => normalizeOcrMarkdown(text), [text]);
  const charCount = normalized.length;
  const lineCount = normalized.split("\n").length;
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
    <div
      className={cn(
        "panel-elevated rounded-xl overflow-hidden",
        className
      )}
    >
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
              {hasTables ? ` · ${t("hasTables")}` : ""}
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
        <TabsContent value="preview" className="mt-0 p-4 max-h-[520px] overflow-y-auto">
          <MarkdownPreview text={normalized} />
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
