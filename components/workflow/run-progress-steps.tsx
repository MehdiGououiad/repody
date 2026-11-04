"use client";

import { Brain, CheckCircle2, Circle, Clock, Code, Loader2, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import type { RunProgress } from "@/lib/api/run";
import { cn, formatDurationMs } from "@/lib/utils";

/** Worker step ids: `extract-<document>`, `rules` (prefixed `worker-` in a test run). */
function stepKind(step: RunProgress["steps"][number]): "extract" | "rule" | null {
  const id = step.id.replace(/^worker-/, "");
  return id.startsWith("extract-") ? "extract" : id === "rules" ? "rule" : null;
}

function stepIcon(step: RunProgress["steps"][number]) {
  if (step.status === "done") {
    return <CheckCircle2 className="h-4 w-4 text-success shrink-0" />;
  }
  if (step.status === "active") {
    return <Loader2 className="h-4 w-4 text-accent-blue animate-spin shrink-0" />;
  }
  return <Circle className="h-4 w-4 text-on-surface-variant/40 shrink-0" />;
}

function modeBadge(step: RunProgress["steps"][number]) {
  if (stepKind(step) === "extract") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-accent-blue/10 px-1.5 py-0.5 text-[10px] font-medium text-accent-blue">
        <Brain className="h-3 w-3" />
        Document model
      </span>
    );
  }
  if (stepKind(step) === "rule") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-medium text-on-surface-variant">
        <Code className="h-3 w-3" />
        Logic rule
      </span>
    );
  }
  return null;
}

function cacheBadge(step: RunProgress["steps"][number]) {
  if (!step.cacheHit) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success">
      <Sparkles className="h-3 w-3" />
      Cached result
    </span>
  );
}

function useActiveStepElapsed(activeStepId: string | undefined) {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (!activeStepId) return;
    const started = Date.now();
    const update = () => setElapsedMs(Date.now() - started);
    update();
    const timer = window.setInterval(update, 500);
    return () => window.clearInterval(timer);
  }, [activeStepId]);

  return activeStepId ? elapsedMs : 0;
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
  const total = progress.steps.length;
  const activeStep = progress.steps.find((s) => s.status === "active");
  const elapsedMs = useActiveStepElapsed(activeStep?.id);
  const showQueue = progress.queuePosition != null && progress.queueDepth != null;
  const queueStep = progress.steps.find((s) => s.id.replace(/^worker-/, "") === "queue");
  const isQueued =
    queueStep != null && (queueStep.status === "active" || queueStep.status === "pending");

  return (
    <div className={cn("space-y-3", className)}>
      {showQueue || isQueued ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-xs text-on-surface">
          <p className="font-medium">
            {progress.queuePosition != null && progress.queueDepth != null
              ? t("queuePosition", {
                  position: progress.queuePosition,
                  depth: progress.queueDepth,
                })
              : t("queueWaiting")}
          </p>
          <p className="text-on-surface-variant mt-1 leading-snug">
            {queueStep?.detail ?? activeStep?.detail ?? t("queueOrdered")}
          </p>
        </div>
      ) : null}
      <div className="rounded-lg border border-accent-blue/20 bg-accent-blue/5 px-3 py-2.5 space-y-1">
        <div className="flex items-center justify-between gap-2 text-xs">
          <p className="text-on-surface font-medium truncate">{progress.label}</p>
          <span className="text-on-surface-variant/70 shrink-0 tabular-nums">
            {doneCount}/{total}
          </span>
        </div>
        {activeStep?.detail && (
          <p className="text-[11px] text-on-surface-variant leading-snug">{activeStep.detail}</p>
        )}
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
              {stepIcon(step)}
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
                    {step.label}
                  </p>
                  {step.durationMs != null && step.durationMs > 0 ? (
                    <span className="inline-flex items-center gap-0.5 shrink-0 text-[10px] tabular-nums text-on-surface-variant">
                      <Clock className="h-3 w-3" />
                      {formatDurationMs(step.durationMs)}
                    </span>
                  ) : step.status === "active" && activeStep?.id === step.id ? (
                    <span className="inline-flex items-center gap-0.5 shrink-0 text-[10px] tabular-nums text-accent-blue">
                      <Clock className="h-3 w-3" />
                      {formatDurationMs(elapsedMs)}
                    </span>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {modeBadge(step)}
                  {cacheBadge(step)}
                </div>
                {step.detail && (
                  <p className="text-[10px] text-on-surface-variant/90 leading-relaxed">
                    {step.detail}
                  </p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
