"use client";

import { Check, Copy } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCopyToClipboard } from "@/lib/hooks/use-copy-to-clipboard";
import { cn } from "@/lib/utils";

export function CopyButton({ text, className }: { text: string; className?: string }) {
  const tCommon = useTranslations("common");
  const { copied, copy } = useCopyToClipboard(1800);

  return (
    <button
      type="button"
      onClick={() => void copy(text)}
      aria-label={copied ? tCommon("copied") : tCommon("copy")}
      className={cn(
        "inline-flex items-center gap-1 text-2xs font-mono transition-colors shrink-0",
        copied ? "text-pass-ink" : "text-ink-3 hover:text-ink",
        className
      )}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? tCommon("copied") : tCommon("copy")}
    </button>
  );
}
