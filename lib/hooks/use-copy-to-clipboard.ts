"use client";

import { useCallback, useState } from "react";

/** Clipboard write with a transient `copied` flag; `copy` resolves to false on failure. */
export function useCopyToClipboard(resetMs = 2000) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        return false;
      }
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
      return true;
    },
    [resetMs]
  );

  return { copied, copy };
}
