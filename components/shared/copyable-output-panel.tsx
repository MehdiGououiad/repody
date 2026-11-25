"use client";

import { toast } from "@ui-sdk/react/toast";
import { Check, Copy } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
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

/** A copy button whose icon cross-fades to a tick once copied. */
export function CopyIconButton({
  text,
  label,
  copiedLabel,
  failedLabel,
  className,
}: {
  text: string;
  label: string;
  copiedLabel: string;
  failedLabel: string;
  className?: string;
}) {
  const { copied, copy } = useCopyToClipboard();
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      className={className}
      aria-label={copied ? copiedLabel : label}
      onClick={async () => {
        if (!(await copy(text))) toast.error(failedLabel);
      }}
    >
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={copied ? "copied" : "copy"}
          initial={{ opacity: 0, scale: 0.4 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.4 }}
          transition={{ type: "spring", duration: 0.3, bounce: 0 }}
          className="flex"
        >
          {copied ? <Check className="text-pass" /> : <Copy />}
        </motion.span>
      </AnimatePresence>
    </Button>
  );
}

/** Model output: Preview and Source tabs, a copy button, the content below. */
export function CopyableOutputPanel({
  labels,
  copyText,
  preview,
  source,
  className,
}: {
  icon?: ReactNode;
  headerClassName?: string;
  labels: CopyableOutputLabels;
  copyText: string;
  preview: ReactNode;
  source: ReactNode;
  className?: string;
}) {
  return (
    <Tabs
      defaultValue="preview"
      className={cn("overflow-hidden rounded-md shadow-panel", className)}
    >
      <div className="flex h-9 items-center gap-2 border-b border-line ps-1.5 pe-1">
        <TabsList aria-label={labels.title}>
          <TabsTab value="preview" className="h-6 px-2 text-xs">
            {labels.previewTab}
          </TabsTab>
          <TabsTab value="source" className="h-6 px-2 text-xs">
            {labels.sourceTab}
          </TabsTab>
        </TabsList>
        <span className="ms-auto truncate text-xs text-ink-4">{labels.subtitle}</span>
        <CopyIconButton
          text={copyText}
          label={labels.copy}
          copiedLabel={labels.copied}
          failedLabel={labels.copyFailed}
        />
      </div>
      <TabsPanel value="preview">{preview}</TabsPanel>
      <TabsPanel value="source">{source}</TabsPanel>
    </Tabs>
  );
}

/** Monospace block for raw text or JSON inside a panel tab. */
export function OutputPre({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return (
    <pre
      className={cn(
        "max-h-[480px] overflow-auto overscroll-contain whitespace-pre-wrap break-words bg-field p-3 font-mono text-xs leading-relaxed",
        muted ? "text-ink-3" : "text-ink-2",
      )}
    >
      {children}
    </pre>
  );
}
