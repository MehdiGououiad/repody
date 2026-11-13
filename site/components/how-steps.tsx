"use client";

import { MotionConfig, motion, useInView } from "motion/react";
import { useRef } from "react";

const ease = [0.23, 1, 0.32, 1] as const;

/** The steps on one line that draws as the section comes into view, the steps lighting in order. Once. */
export function HowSteps({ steps }: { steps: { title: string; body: string }[] }) {
  const ref = useRef<HTMLOListElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  return (
    <MotionConfig reducedMotion="user">
      <ol
        ref={ref}
        className="relative grid gap-8 md:grid-cols-[repeat(var(--steps),minmax(0,1fr))] md:gap-6"
        style={{ "--steps": steps.length } as React.CSSProperties}
      >
        <span
          className="absolute start-[13px] top-0 bottom-0 w-px bg-line md:start-0 md:end-0 md:top-[13px] md:bottom-auto md:h-px md:w-auto"
          aria-hidden
        >
          <motion.span
            className="block size-full origin-top bg-accent md:origin-left"
            initial={{ scaleX: 0, scaleY: 0 }}
            animate={inView ? { scaleX: 1, scaleY: 1 } : undefined}
            transition={{ duration: 1.4, ease }}
          />
        </span>
        {steps.map((step, i) => (
          <li key={step.title} className="relative flex gap-4 md:flex-col md:gap-5">
            <motion.span
              className="relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full border border-line-strong bg-panel text-xs font-semibold tabular-nums text-ink-3"
              initial={false}
              animate={
                inView
                  ? {
                      backgroundColor: "var(--accent)",
                      color: "var(--on-accent)",
                      borderColor: "var(--accent)",
                    }
                  : undefined
              }
              transition={{ delay: 0.25 + i * 0.32, duration: 0.25 }}
            >
              {i + 1}
            </motion.span>
            <div>
              <h3 className="text-[0.9375rem] font-semibold text-ink">{step.title}</h3>
              <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-ink-3">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </MotionConfig>
  );
}
