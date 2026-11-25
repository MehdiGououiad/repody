"use client";

import {
  Progress,
  ProgressIndicator,
  ProgressLabel,
  ProgressTrack,
  ProgressValue,
} from "@ui-sdk/react/progress";
import {
  Check,
  Clock,
  Cpu,
  FileCheck2,
  ListChecks,
  type LucideIcon,
  ScanText,
  Users,
  X,
} from "lucide-react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { RunProgress } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";

type Step = RunProgress["steps"][number];

const KIND_ICON: Record<Step["kind"], LucideIcon> = {
  queue: Users,
  model: Cpu,
  extract: ScanText,
  rules: ListChecks,
  finalize: FileCheck2,
};

const spring = { type: "spring", stiffness: 420, damping: 28 } as const;

function useElapsed(activeStepId: string | undefined): number {
  const [elapsed, setElapsed] = useState({ id: activeStepId, ms: 0 });
  useEffect(() => {
    if (!activeStepId) return;
    const started = Date.now();
    const timer = window.setInterval(
      () => setElapsed({ id: activeStepId, ms: Date.now() - started }),
      250,
    );
    return () => window.clearInterval(timer);
  }, [activeStepId]);
  return elapsed.id === activeStepId ? elapsed.ms : 0;
}

function Node({ step }: { step: Step }) {
  const failed = step.status === "done" && step.failed;
  return (
    <span className="relative flex size-6 shrink-0 items-center justify-center">
      {step.status === "active" ? (
        <motion.span
          className="absolute inset-0 rounded-full bg-accent/30"
          animate={{ scale: [1, 1.7], opacity: [0.6, 0] }}
          transition={{ duration: 1.4, repeat: Number.POSITIVE_INFINITY, ease: "easeOut" }}
        />
      ) : null}
      <motion.span
        className={cn(
          "relative flex size-6 items-center justify-center rounded-full border-2 transition-colors duration-300",
          step.status === "pending" && "border-line bg-panel",
          step.status === "active" && "border-accent bg-accent/10",
          step.status === "done" && !failed && "border-pass bg-pass",
          failed && "border-fail bg-fail",
        )}
        animate={{ scale: step.status === "active" ? 1.08 : 1 }}
        transition={spring}
      >
        <AnimatePresence mode="wait" initial={false}>
          {step.status === "done" ? (
            <motion.span
              key="done"
              initial={{ scale: 0, rotate: -45 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={spring}
            >
              {failed ? (
                <X className="size-3.5 text-white" strokeWidth={3} />
              ) : (
                <Check className="size-3.5 text-white" strokeWidth={3} />
              )}
            </motion.span>
          ) : step.status === "active" ? (
            <motion.span
              key="active"
              className="size-2 rounded-full bg-accent"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            />
          ) : null}
        </AnimatePresence>
      </motion.span>
    </span>
  );
}

function Connector({ done }: { done: boolean }) {
  return (
    <span className="absolute left-[11px] top-7 bottom-[-6px] w-0.5 overflow-hidden rounded-full bg-line">
      <motion.span
        className="block h-full w-full origin-top bg-pass"
        initial={false}
        animate={{ scaleY: done ? 1 : 0 }}
        transition={{ duration: 0.45, ease: "easeInOut" }}
      />
    </span>
  );
}

function Sweep({ label }: { label: string }) {
  return (
    <Progress value={null} aria-label={label} className="mt-2">
      <ProgressTrack className="relative h-1 w-full overflow-hidden rounded-full bg-accent/10">
        <ProgressIndicator className="block h-full rounded-full bg-accent data-indeterminate:w-1/3 data-indeterminate:animate-[sweep_1.3s_ease-in-out_infinite] motion-reduce:data-indeterminate:w-full motion-reduce:data-indeterminate:animate-none" />
      </ProgressTrack>
    </Progress>
  );
}

function ColdStart({ elapsedMs }: { elapsedMs: number }) {
  const t = useTranslations("runProgress");
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="overflow-hidden"
    >
      <div className="mt-2 rounded-lg border border-accent/25 p-3">
        <div className="flex items-center gap-3">
          <div className="relative flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent/15">
            <motion.span
              className="absolute inset-0 rounded-lg border-2 border-accent/40"
              animate={{ opacity: [0.2, 1, 0.2] }}
              transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY }}
            />
            <Cpu className="size-5 text-accent-ink" />
          </div>
          <div className="flex items-end gap-0.5" aria-hidden>
            {Array.from({ length: 10 }, (_, i) => i).map((i) => (
              <motion.span
                key={i}
                className="w-1 rounded-full bg-accent"
                animate={{ height: [4, 16, 4], opacity: [0.35, 1, 0.35] }}
                transition={{
                  duration: 1.1,
                  repeat: Number.POSITIVE_INFINITY,
                  delay: i * 0.09,
                  ease: "easeInOut",
                }}
              />
            ))}
          </div>
          <span className="ml-auto text-2xs font-semibold tabular-nums text-accent-ink">
            {formatDurationMs(elapsedMs)}
          </span>
        </div>
        <p className="mt-2.5 text-2xs leading-relaxed text-ink-3">{t("steps.modelWakingHint")}</p>
        <Progress value={null} aria-label={t("steps.modelWaking")} className="mt-2.5">
          <ProgressTrack className="relative h-1.5 w-full overflow-hidden rounded-full bg-accent/10">
            <ProgressIndicator className="block h-full rounded-full bg-accent data-indeterminate:w-1/3 data-indeterminate:animate-[sweep_1.6s_ease-in-out_infinite] motion-reduce:data-indeterminate:w-full motion-reduce:data-indeterminate:animate-none" />
          </ProgressTrack>
        </Progress>
      </div>
    </motion.div>
  );
}

export function useStepTitle() {
  const t = useTranslations("runProgress");
  return (step: Step) => {
    switch (step.kind) {
      case "queue":
        return t("steps.queue");
      case "model":
        if (step.status === "done")
          return step.coldStart ? t("steps.modelStarted") : t("steps.modelReady");
        return step.coldStart ? t("steps.modelWaking") : t("steps.model");
      case "extract":
        return t("steps.extract", { document: step.documentType || t("steps.document") });
      case "rules":
        return t("steps.rules", { count: step.ruleCount ?? 0 });
      case "finalize":
        return t("steps.finalize");
    }
  };
}

export function RunProgressSteps({
  progress,
  totalElapsedMs,
  className,
}: {
  progress: RunProgress;
  totalElapsedMs?: number;
  className?: string;
}) {
  const t = useTranslations("runProgress");
  const steps = progress.steps;
  const doneCount = steps.filter((s) => s.status === "done").length;
  const activeSteps = steps.filter((s) => s.status === "active");
  const elapsedMs = useElapsed(activeSteps[0]?.id);
  const queued = steps.some((s) => s.kind === "queue" && s.status !== "done");

  const title = useStepTitle();
  const allDone = steps.length > 0 && doneCount === steps.length;
  const current = activeSteps.length
    ? activeSteps.map(title).join(" · ")
    : allDone
      ? t("steps.complete")
      : t("steps.waiting");

  return (
    <MotionConfig reducedMotion="user">
      <div className={cn("space-y-3", className)}>
        <AnimatePresence initial={false}>
          {queued ? (
            <motion.div
              key="queue"
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, height: 0, marginBottom: 0 }}
              className="overflow-hidden rounded-lg bg-warn-wash px-3 py-2.5 text-sm text-ink"
            >
              <p className="font-medium">{t("queueWaiting")}</p>
              <p className="mt-0.5 text-xs text-ink-3">{t("queueOrdered")}</p>
            </motion.div>
          ) : null}
        </AnimatePresence>

        <Progress
          value={steps.length ? doneCount : null}
          max={Math.max(steps.length, 1)}
          className="rounded-lg px-1 py-1"
        >
          <div className="flex items-center justify-between gap-2 text-xs">
            <ProgressLabel className="relative h-4 min-w-0 flex-1 overflow-hidden">
              <AnimatePresence mode="popLayout" initial={false}>
                <motion.span
                  key={current}
                  className="block truncate font-medium text-ink"
                  initial={{ y: 14, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -14, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  {current}
                </motion.span>
              </AnimatePresence>
            </ProgressLabel>
            <span className="flex shrink-0 items-center gap-2 tabular-nums text-ink-3/70">
              {totalElapsedMs ? <span>{formatDurationMs(totalElapsedMs)}</span> : null}
              <ProgressValue>{`${doneCount}/${steps.length}`}</ProgressValue>
            </span>
          </div>
          <ProgressTrack className="mt-2 block h-1 w-full overflow-hidden rounded-full bg-accent/10">
            <ProgressIndicator className="block h-full rounded-full bg-accent transition-[width] duration-300 ease-out data-indeterminate:w-1/3 data-indeterminate:animate-[sweep_1.3s_ease-in-out_infinite] motion-reduce:transition-none" />
          </ProgressTrack>
        </Progress>

        <ol className="max-h-[30rem] space-y-1.5 overflow-y-auto pr-1">
          {steps.map((step, index) => {
            const Icon = KIND_ICON[step.kind];
            const active = step.status === "active";
            const failed = step.status === "done" && step.failed;
            const stepTitle = title(step);
            return (
              <motion.li
                key={step.id}
                layout="position"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="relative flex gap-3 pb-1.5"
              >
                {index < steps.length - 1 ? <Connector done={step.status === "done"} /> : null}
                <Node step={step} />
                <div
                  className={cn(
                    "min-w-0 flex-1 rounded-lg border px-2.5 py-1.5 transition-colors duration-300",
                    active ? "border-accent/25 bg-accent/5" : "border-transparent",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className={cn(
                        "flex items-center gap-1.5 text-xs leading-snug",
                        active && "font-semibold text-ink",
                        step.status === "done" && "text-ink",
                        step.status === "pending" && "text-ink-3/70",
                      )}
                    >
                      <Icon
                        className={cn(
                          "size-3.5 shrink-0",
                          active ? "text-accent-ink" : "text-ink-3",
                        )}
                      />
                      {stepTitle}
                    </p>
                    <AnimatePresence mode="wait" initial={false}>
                      {step.durationMs ? (
                        <motion.span
                          key="took"
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="inline-flex shrink-0 items-center gap-0.5 text-2xs tabular-nums text-ink-3"
                        >
                          <Clock className="size-3" />
                          {formatDurationMs(step.durationMs)}
                        </motion.span>
                      ) : step.id === activeSteps[0]?.id ? (
                        <motion.span
                          key="running"
                          exit={{ opacity: 0 }}
                          className="inline-flex shrink-0 items-center gap-0.5 text-2xs tabular-nums text-accent-ink"
                        >
                          <Clock className="size-3" />
                          {formatDurationMs(elapsedMs)}
                        </motion.span>
                      ) : null}
                    </AnimatePresence>
                  </div>

                  {step.kind === "model" && step.status === "done" && step.coldStart ? (
                    <p className="mt-0.5 text-2xs leading-relaxed text-ink-3/90">
                      {t("steps.modelStartedHint")}
                    </p>
                  ) : null}
                  {step.kind === "extract" && step.status === "done" ? (
                    <p
                      className={cn(
                        "mt-0.5 flex items-center gap-1 text-2xs leading-relaxed",
                        failed ? "text-fail-ink" : "text-ink-3/90",
                      )}
                    >
                      {failed
                        ? t("steps.extractFailed")
                        : t("steps.extracted", { count: step.fieldsExtracted ?? 0 })}
                    </p>
                  ) : null}

                  <AnimatePresence initial={false}>
                    {step.kind === "model" && active && step.coldStart ? (
                      <ColdStart key="cold" elapsedMs={elapsedMs} />
                    ) : null}
                  </AnimatePresence>
                  {active && !(step.kind === "model" && step.coldStart) && step.kind !== "queue" ? (
                    <Sweep label={stepTitle} />
                  ) : null}
                </div>
              </motion.li>
            );
          })}
        </ol>
      </div>
    </MotionConfig>
  );
}
