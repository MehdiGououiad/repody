"use client";

import { Check, Copy } from "lucide-react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCopyToClipboard } from "@/lib/hooks/use-copy-to-clipboard";
import { cn } from "@/lib/utils";

export interface CopyableOutputLabels {
  title: string;
  subtitle: string;
  copy: string;
  copied: string;
  copyFailed: string;
  previewTab: string;
  sourceTab: string;
}

const TAB_TRIGGER_CLASS =
  "rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-0 pb-2 text-xs";

/** Model output card: header with copy action, then Preview / Source tabs. */
export function CopyableOutputPanel({
  icon,
  labels,
  copyText,
  preview,
  source,
  headerClassName,
  className,
}: {
  icon: ReactNode;
  labels: CopyableOutputLabels;
  copyText: string;
  preview: ReactNode;
  source: ReactNode;
  headerClassName?: string;
  className?: string;
}) {
  const { copied, copy } = useCopyToClipboard();

  const handleCopy = async () => {
    if (await copy(copyText)) toast.success(labels.copied);
    else toast.error(labels.copyFailed);
  };

  return (
    <div className={cn("panel-elevated rounded-xl overflow-hidden", className)}>
      <div
        className={cn(
          "flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-gradient-to-r to-transparent",
          headerClassName
        )}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          {icon}
          <div className="min-w-0">
            <p className="text-sm font-semibold text-on-surface">{labels.title}</p>
            <p className="text-[11px] text-on-surface-variant truncate">{labels.subtitle}</p>
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
          {copied ? labels.copied : labels.copy}
        </Button>
      </div>

      <Tabs defaultValue="preview" className="w-full">
        <div className="px-4 pt-2 border-b border-border bg-surface-container-lowest">
          <TabsList className="h-8 bg-transparent p-0 gap-4">
            <TabsTrigger value="preview" className={TAB_TRIGGER_CLASS}>
              {labels.previewTab}
            </TabsTrigger>
            <TabsTrigger value="source" className={TAB_TRIGGER_CLASS}>
              {labels.sourceTab}
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="preview" className="mt-0 p-0">
          {preview}
        </TabsContent>
        <TabsContent value="source" className="mt-0 p-0">
          {source}
        </TabsContent>
      </Tabs>
    </div>
  );
}

/** Monospace block used for raw text / JSON inside a panel tab. */
export function OutputPre({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return (
    <pre
      className={cn(
        "max-h-[520px] overflow-auto p-4 text-[11px] leading-relaxed font-mono bg-surface-container-lowest whitespace-pre-wrap break-words",
        muted ? "text-on-surface-variant" : "text-on-surface"
      )}
    >
      {children}
    </pre>
  );
}
