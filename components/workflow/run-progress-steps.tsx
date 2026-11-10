"use client";

import { Brain, CheckCircle2, Circle, Clock, Code, Loader2, Sparkles, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { RunProgress } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";

type Step = RunProgress["steps"][number];

function StepIcon({ step }: { step: Step }) {
  if (step.status === "done" && step.failed) {
    return <XCircle className="h-4 w-4 text-danger shrink-0" />;
  }
  if (step.status === "done") return <CheckCircle2 className="h-4 w-4 text-success shrink-0" />;
  if (step.status === "active") {
    return <Loader2 className="h-4 w-4 text-accent-blue animate-spin shrink-0" />;
  }
  return <Circle className="h-4 w-4 text-on-surface-variant/40 shrink-0" />;
}

function Badge({
  tone,
  icon: Icon,
  children,
}: {
  tone: "blue" | "neutral" | "success";
  icon: typeof Brain;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium",
        tone === "blue" && "bg-accent-blue/10 text-accent-blue",
        tone === "neutral" && "bg-surface-container text-on-surface-variant",
        tone === "success" && "bg-success/10 text-success"
      )}
    >
      <Icon className="h-3 w-3" />
      {children}
    </span>
  );
}

/** Milliseconds since the active step started (restarts when another step becomes active). */
function useElapsed(activeStepId: string | undefined): number {
  const [elapsed, setElapsed] = useState({ id: activeStepId, ms: 0 });
  useEffect(() => {
    if (!activeStepId) return;
    const started = Date.now();
    const timer = window.setInterval(
      () => setElapsed({ id: activeStepId, ms: Date.now() - started }),
      500
    );
    return () => window.clearInterval(timer);
  }, [activeStepId]);
  return elapsed.id === activeStepId ? elapsed.ms : 0;
}

export function RunProgressSteps({
  progress,
  className,
}: {
  progress: RunProgress;
  className?: string;
}) {
  const t = useTranslations("runProgress");
  const doneCount = progress.steps.filter((s) => s.status === "done").length;
  const activeSteps = progress.steps.filter((s) => s.status === "active");
  const elapsedMs = useElapsed(activeSteps[0]?.id);
  const queued = progress.steps.some((s) => s.kind === "queue" && s.status !== "done");

  const title = (step: Step) => {
    switch (step.kind) {
      case "queue":
        return t("steps.queue");
      case "extract":
        return t("steps.extract", { document: step.documentType || t("steps.document") });
      case "rules":
        return t("steps.rules", { count: step.ruleCount ?? 0 });
      case "finalize":
        return t("steps.finalize");
    }
  };
  const current = activeSteps.length ? activeSteps.map(title).join(" · ") : t("steps.waiting");

  return (
    <div className={cn("space-y-3", className)}>
      {queued ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-xs text-on-surface">
          <p className="font-medium">
            {progress.queuePosition != null && progress.queueDepth != null
              ? t("queuePosition", { position: progress.queuePosition, depth: progress.queueDepth })
              : t("queueWaiting")}
          </p>
          <p className="text-on-surface-variant mt-1 leading-snug">{t("queueOrdered")}</p>
        </div>
      ) : null}
      <div className="rounded-lg border border-accent-blue/20 bg-accent-blue/5 px-3 py-2.5">
        <div className="flex items-center justify-between gap-2 text-xs">
          <p className="text-on-surface font-medium truncate">{current}</p>
          <span className="text-on-surface-variant/70 shrink-0 tabular-nums">
            {doneCount}/{progress.steps.length}
          </span>
        </div>
      </div>
      <ul className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {progress.steps.map((step) => (
          <li
            key={step.id}
            className={cn(
              "rounded-lg px-2.5 py-2 border border-transparent",
              step.status === "active" && "bg-accent-blue/5 border-accent-blue/20",
              step.status === "done" && "opacity-90"
            )}
          >
            <div className="flex items-start gap-2.5">
              <StepIcon step={step} />
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <p
                    className={cn(
                      "text-xs leading-snug",
                      step.status === "active"
                        ? "text-on-surface font-semibold"
                        : "text-on-surface-variant"
                    )}
                  >
                    {title(step)}
                  </p>
                  {step.durationMs ? (
                    <span className="inline-flex items-center gap-0.5 shrink-0 text-[10px] tabular-nums text-on-surface-variant">
                      <Clock className="h-3 w-3" />
                      {formatDurationMs(step.durationMs)}
                    </span>
                  ) : step.id === activeSteps[0]?.id ? (
                    <span className="inline-flex items-center gap-0.5 shrink-0 text-[10px] tabular-nums text-accent-blue">
                      <Clock className="h-3 w-3" />
                      {formatDurationMs(elapsedMs)}
                    </span>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {step.kind === "extract" ? (
                    <Badge tone="blue" icon={Brain}>
                      {t("badges.model")}
                    </Badge>
                  ) : null}
                  {step.kind === "rules" ? (
                    <Badge tone="neutral" icon={Code}>
                      {t("badges.rules")}
                    </Badge>
                  ) : null}
                  {step.cacheHit ? (
                    <Badge tone="success" icon={Sparkles}>
                      {t("badges.cached")}
                    </Badge>
                  ) : null}
                </div>
                {step.kind === "extract" && step.status === "done" ? (
                  <p
                    className={cn(
                      "text-[10px] leading-relaxed",
                      step.failed ? "text-danger" : "text-on-surface-variant/90"
                    )}
                  >
                    {step.failed
                      ? t("steps.extractFailed")
                      : t("steps.extracted", { count: step.fieldsExtracted ?? 0 })}
                  </p>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
