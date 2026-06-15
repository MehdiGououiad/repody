"use client";

import { useEffect, useState } from "react";
import {
  Brain,
  CheckCircle2,
  Circle,
  Clock,
  Code,
  Loader2,
  Snowflake,
  Sparkles,
} from "lucide-react";
import { useTranslations } from "next-intl";

import type { RunProgress } from "@/lib/api/test-run";
import { usePlatformConfig } from "@/lib/hooks/use-catalog-queries";
import { formatDurationMs } from "@/lib/types/audit";
import { cn } from "@/lib/utils";

const GPU_COLD_START_ESCALATE_MS = 12_000;

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
  if (step.mode === "document_model") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-accent-blue/10 px-1.5 py-0.5 text-[10px] font-medium text-accent-blue">
        <Brain className="h-3 w-3" />
        Document model
      </span>
    );
  }
  if (step.mode === "schema") {
    return (
      <span className="rounded bg-surface-container px-1.5 py-0.5 text-[10px] text-on-surface-variant">
        Schema only
      </span>
    );
  }
  if (step.kind === "llm") {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
        <Brain className="h-3 w-3" />
        LLM rule
      </span>
    );
  }
  if (step.kind === "logic") {
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
  if (!step.cacheHit && !step.detail?.toLowerCase().includes("reusing cached")) {
    return null;
  }
  return (
    <span className="inline-flex items-center gap-1 rounded bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success">
      <Sparkles className="h-3 w-3" />
      Cached result
    </span>
  );
}

function coldStartBadge(step: RunProgress["steps"][number]) {
  if (!step.gpuColdStartHint) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:text-sky-300">
      <Snowflake className="h-3 w-3" />
      Serverless GPU
    </span>
  );
}

function useActiveStepElapsed(activeStepId: string | undefined) {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (!activeStepId) {
      setElapsedMs(0);
      return;
    }
    const started = Date.now();
    setElapsedMs(0);
    const timer = window.setInterval(() => {
      setElapsedMs(Date.now() - started);
    }, 500);
    return () => window.clearInterval(timer);
  }, [activeStepId]);

  return elapsedMs;
}

export function RunProgressSteps({
  progress,
  className,
}: {
  progress: RunProgress;
  className?: string;
}) {
  const t = useTranslations("runProgress");
  const platform = usePlatformConfig();
  const inferenceMode = platform.data?.inferenceMode?.toLowerCase();
  const doneCount = progress.steps.filter((s) => s.status === "done").length;
  const total = progress.steps.length;
  const activeStep = progress.steps.find((s) => s.status === "active");
  const elapsedMs = useActiveStepElapsed(activeStep?.id);
  const showQueue =
    progress.queuePosition != null &&
    progress.queueDepth != null &&
    progress.queueDepth > 1;

  const serverlessGpu = inferenceMode === "vllm";
  const extractStepActive =
    activeStep?.mode === "document_model" && activeStep.status === "active";
  const coldStartContext =
    serverlessGpu &&
    extractStepActive &&
    !activeStep?.cacheHit &&
    (activeStep.gpuColdStartHint === true || elapsedMs >= GPU_COLD_START_ESCALATE_MS);
  const showColdStartBanner =
    coldStartContext &&
    (activeStep?.gpuColdStartHint === true || elapsedMs >= GPU_COLD_START_ESCALATE_MS);

  return (
    <div className={cn("space-y-3", className)}>
      {showQueue ? (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-xs text-on-surface">
          <p className="font-medium">
            Queue position {progress.queuePosition} of {progress.queueDepth}
          </p>
          <p className="text-on-surface-variant mt-1 leading-snug">
            {activeStep?.detail ??
              (serverlessGpu ? t("queueServerless") : "Runs are processed in order.")}
          </p>
        </div>
      ) : null}
      {showColdStartBanner ? (
        <div
          role="status"
          className="rounded-lg border border-sky-500/35 bg-sky-500/10 px-3 py-2.5 text-xs text-on-surface"
        >
          <p className="font-medium inline-flex items-center gap-1.5">
            <Snowflake className="h-3.5 w-3.5 text-sky-600 dark:text-sky-300 shrink-0" />
            {t("gpuColdStartTitle")}
          </p>
          <p className="text-on-surface-variant mt-1 leading-snug">
            {elapsedMs >= GPU_COLD_START_ESCALATE_MS
              ? t("gpuColdStartActive", { elapsed: formatDurationMs(elapsedMs) })
              : t("gpuColdStartHint")}
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
                  {step.durationMs != null && step.durationMs > 0 && (
                    <span className="inline-flex items-center gap-0.5 shrink-0 text-[10px] tabular-nums text-on-surface-variant">
                      <Clock className="h-3 w-3" />
                      {formatDurationMs(step.durationMs)}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {modeBadge(step)}
                  {cacheBadge(step)}
                  {coldStartBadge(step)}
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
