"use client";

import { ArrowUpRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ReportBody, ReportVerdict } from "@/components/audit/report";
import { Button } from "@/components/ui/button";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import type { RunView } from "@/lib/api/runs";

/** The live run timeline while it runs, then the report; nothing before the first run. */
export function TestRunResults({ run, starting }: { run: RunView; starting: boolean }) {
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
            className="max-w-md"
          >
            {run.phase === "running" && run.progress ? (
              <RunProgressSteps progress={run.progress} />
            ) : (
              <p className="text-sm text-ink-3">{t("progress.starting")}</p>
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
