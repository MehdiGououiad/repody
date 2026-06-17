"use client";

import { ListOrdered, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useQueueLive } from "@/lib/hooks/use-queue-live";
import { cn } from "@/lib/utils";

export function QueueLiveBadge({ className }: { className?: string }) {
  const t = useTranslations("dashboard.queueLive");
  const queue = useQueueLive();

  const { runningRuns, queuedRuns } = queue;
  const active = runningRuns > 0 || queuedRuns > 0;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs",
        active
          ? "border-accent-blue/30 bg-accent-blue/5 text-on-surface"
          : "border-outline-variant/40 bg-surface-container-low text-on-surface-variant",
        className
      )}
      role="status"
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2 shrink-0">
        {active ? (
          <>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-blue opacity-50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-blue" />
          </>
        ) : (
          <span className="relative inline-flex h-2 w-2 rounded-full bg-on-surface-variant/35" />
        )}
      </span>
      <ListOrdered className="h-3.5 w-3.5 shrink-0 text-accent-blue" aria-hidden />
      {active ? (
        <span className="font-medium tabular-nums">
          {t("counts", { running: runningRuns, queued: queuedRuns })}
        </span>
      ) : (
        <span>{t("idle")}</span>
      )}
      {runningRuns > 0 ? (
        <Loader2 className="h-3 w-3 animate-spin text-accent-blue shrink-0" aria-hidden />
      ) : null}
    </div>
  );
}
