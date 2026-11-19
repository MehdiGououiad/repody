"use client";

import { Progress, ProgressIndicator, ProgressLabel, ProgressTrack } from "@ui-sdk/react/progress";
import { ArrowUpRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ReportBody, ReportVerdict } from "@/components/audit/report";
import { Button } from "@/components/ui/button";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import type { RunView } from "@/lib/api/runs";
import { formatDurationMs } from "@/lib/utils";

export function TestRunResults({
  run,
  starting,
  elapsedMs = 0,
}: {
  run: RunView;
  starting: boolean;
  elapsedMs?: number;
}) {
  const t = useTranslations("workflows.builder.test");
  const phase = starting ? "running" : run.phase;
  if (phase === "idle" || phase === "failed") return null;
  return (
    <section aria-live="polite" className="flex flex-col gap-6">
      <AnimatePresence mode="wait" initial={false}>
        {phase === "running" ? (
          <motion.div
            key="running"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.12 } }}
            className="max-w-lg rounded-xl bg-panel p-4 shadow-[0_0_0_1px_var(--line)]"
          >
            {run.phase === "running" && run.progress ? (
              <RunProgressSteps progress={run.progress} totalElapsedMs={elapsedMs} />
            ) : (
              <Progress value={null} className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <ProgressLabel className="font-medium text-ink">
                    {t("progress.starting")}
                  </ProgressLabel>
                  <span className="tabular-nums text-ink-3">{formatDurationMs(elapsedMs)}</span>
                </div>
                <ProgressTrack className="relative h-1.5 w-full overflow-hidden rounded-full bg-accent/10">
                  <ProgressIndicator className="block h-full rounded-full bg-accent data-indeterminate:w-1/3 data-indeterminate:animate-[sweep_1.3s_ease-in-out_infinite] motion-reduce:data-indeterminate:w-full motion-reduce:data-indeterminate:animate-none" />
                </ProgressTrack>
              </Progress>
            )}
          </motion.div>
        ) : null}
        {run.phase === "done" && !starting ? (
          <motion.div
            key={`done-${run.result.id}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
            className="flex flex-col gap-6"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <ReportVerdict audit={run.result} />
              <Button
                variant="ghost"
                size="sm"
                render={<Link href={`/audits/${run.result.id}`} target="_blank" />}
              >
                {t("openFullReport")}
                <ArrowUpRight />
              </Button>
            </div>
            <ReportBody audit={run.result} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  );
}
