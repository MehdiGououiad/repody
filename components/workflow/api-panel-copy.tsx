"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

function useCopy(timeout = 1800) {
  const [copied, setCopied] = useState(false);

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), timeout);
    });
  };

  return { copied, copy };
}

export function CopyButton({ text, className }: { text: string; className?: string }) {
  const tCommon = useTranslations("common");
  const { copied, copy } = useCopy();

  return (
    <button
      type="button"
      onClick={() => copy(text)}
      aria-label={copied ? tCommon("copied") : tCommon("copy")}
      className={cn(
        "inline-flex items-center gap-1 text-[10px] font-mono transition-colors shrink-0",
        copied ? "text-success" : "text-on-surface-variant hover:text-on-surface",
        className
      )}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? tCommon("copied") : tCommon("copy")}
    </button>
  );
}
