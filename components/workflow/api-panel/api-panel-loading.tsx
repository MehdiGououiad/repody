"use client";

import { Zap } from "lucide-react";
import { MotionConfig, motion } from "motion/react";
import { useTranslations } from "next-intl";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import type { RunProgress } from "@/lib/types";

export function ApiRunLoadingScreen({
  workflowName,
  progress,
}: {
  workflowName: string;
  progress: RunProgress | null;
}) {
  const t = useTranslations("workflows.builder.api");

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex h-full min-h-[360px] flex-col items-center justify-center gap-6 px-4 text-center">
        <div className="relative size-16">
          <motion.span
            className="absolute inset-0 rounded-full bg-accent/15"
            animate={{ scale: [1, 1.35], opacity: [0.7, 0] }}
            transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY, ease: "easeOut" }}
          />
          <svg viewBox="0 0 64 64" className="absolute inset-0" aria-hidden>
            <circle
              cx="32"
              cy="32"
              r="28"
              fill="none"
              strokeWidth="4"
              className="stroke-primary/15"
            />
            <motion.circle
              cx="32"
              cy="32"
              r="28"
              fill="none"
              strokeWidth="4"
              strokeLinecap="round"
              className="stroke-primary"
              style={{ originX: "50%", originY: "50%" }}
              animate={{ rotate: 360, pathLength: [0.15, 0.6, 0.15] }}
              transition={{
                rotate: { duration: 1.2, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
                pathLength: { duration: 2.4, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
              }}
            />
          </svg>
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            animate={{ scale: [1, 1.12, 1] }}
            transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY }}
          >
            <Zap className="h-6 w-6 text-ink" />
          </motion.div>
        </div>
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
          <p className="text-sm font-semibold text-ink">{t("processing")}</p>
          <p className="mt-1 text-xs text-ink-3">{t("processingHint", { name: workflowName })}</p>
        </motion.div>
        {progress ? (
          <div className="w-full max-w-md text-left">
            <RunProgressSteps progress={progress} />
          </div>
        ) : (
          <p className="text-xs text-ink-3">{t("parseStep")}…</p>
        )}
      </div>
    </MotionConfig>
  );
}
