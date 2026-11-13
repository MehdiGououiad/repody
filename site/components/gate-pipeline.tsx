"use client";

import { MotionConfig, motion, useInView } from "motion/react";
import { useRef } from "react";
import { Glyph } from "./glyph";

/** The release pipeline as a row of gates that pass in order when the section comes into view. Once. */
export function GatePipeline({ gates }: { gates: string[] }) {
  const ref = useRef<HTMLOListElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  return (
    <MotionConfig reducedMotion="user">
      <ol
        ref={ref}
        className="grid gap-px overflow-hidden rounded-xl bg-line shadow-[0_0_0_1px_var(--line)] sm:grid-cols-2 lg:grid-cols-4"
      >
        {gates.map((gate, i) => (
          <li key={gate} className="flex h-14 items-center gap-3 bg-panel px-4">
            <span className="relative size-3.5">
              <motion.span
                className="absolute inset-0"
                initial={{ opacity: 1 }}
                animate={inView ? { opacity: 0 } : undefined}
                transition={{ delay: 0.15 + i * 0.16, duration: 0.15 }}
              >
                <Glyph status="waiting" />
              </motion.span>
              <motion.span
                className="absolute inset-0"
                initial={{ opacity: 0, scale: 0.6 }}
                animate={inView ? { opacity: 1, scale: 1 } : undefined}
                transition={{ delay: 0.15 + i * 0.16, type: "spring", duration: 0.35, bounce: 0 }}
              >
                <Glyph status="passed" />
              </motion.span>
            </span>
            <span className="text-sm text-ink">{gate}</span>
            <span className="ms-auto font-mono text-xs tabular-nums text-ink-4">
              {String(i + 1).padStart(2, "0")}
            </span>
          </li>
        ))}
      </ol>
    </MotionConfig>
  );
}
