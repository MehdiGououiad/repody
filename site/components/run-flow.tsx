"use client";

import { MotionConfig, motion, useScroll, useSpring } from "motion/react";
import { useRef } from "react";

/** The steps of a run on a line that fills as the reader scrolls through them. */
export function RunFlow({ steps }: { steps: { title: string; body: string }[] }) {
  const ref = useRef<HTMLOListElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 75%", "end 55%"] });
  const progress = useSpring(scrollYProgress, { stiffness: 200, damping: 40 });
  return (
    <MotionConfig reducedMotion="user">
      <ol ref={ref} className="relative flex flex-col gap-10">
        <span className="absolute start-[13px] top-2 bottom-2 w-px bg-line" aria-hidden>
          <motion.span
            className="block size-full origin-top bg-accent"
            style={{ scaleY: progress }}
          />
        </span>
        {steps.map((step, i) => (
          <motion.li
            key={step.title}
            className="relative flex gap-5"
            initial={{ opacity: 0.35 }}
            whileInView={{ opacity: 1 }}
            viewport={{ margin: "0px 0px -45% 0px" }}
            transition={{ duration: 0.3 }}
          >
            <span className="relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full bg-panel text-xs font-semibold tabular-nums text-ink-2 shadow-[0_0_0_1px_var(--line-strong)]">
              {i + 1}
            </span>
            <div className="max-w-[560px] pt-0.5">
              <h3 className="text-[1.0625rem] font-semibold text-ink">{step.title}</h3>
              <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-ink-3">{step.body}</p>
            </div>
          </motion.li>
        ))}
      </ol>
    </MotionConfig>
  );
}
