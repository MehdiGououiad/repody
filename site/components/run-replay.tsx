"use client";

import { AnimatePresence, MotionConfig, motion, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import type { Dict } from "@/content";
import { Glyph } from "./glyph";

type Replay = Dict["home"]["replay"];

/** When each phase starts, in ms from the beginning of the loop. */
const PHASES = [0, 700, 3200, 4500, 5200, 5700] as const;
const LOOP_MS = 11_000;
const ease = [0.23, 1, 0.32, 1] as const;

/** The server and the first client render show phase 0; the reduced-motion choice applies after. */
function usePhase(active: boolean, still: boolean) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (still) {
      setPhase(PHASES.length);
      return;
    }
    if (!active) return;
    let timers: number[] = [];
    const run = () => {
      setPhase(0);
      timers = PHASES.map((at, i) => window.setTimeout(() => setPhase(i + 1), at));
    };
    run();
    const loop = window.setInterval(run, LOOP_MS);
    return () => {
      window.clearInterval(loop);
      for (const t of timers) window.clearTimeout(t);
    };
  }, [active, still]);
  return phase;
}

function Step({
  label,
  state,
  extra,
}: {
  label: string;
  state: "waiting" | "running" | "passed";
  extra?: string;
}) {
  return (
    <li className="flex h-8 items-center gap-2.5">
      <Glyph status={state} />
      <span className={`text-sm ${state === "waiting" ? "text-ink-4" : "text-ink"}`}>{label}</span>
      {extra ? <span className="ms-auto text-xs tabular-nums text-ink-3">{extra}</span> : null}
    </li>
  );
}

/**
 * The hero's moment: a real run as the product shows it, replayed. Steps tick, the GPU wakes, the
 * verdict appears with its fields. It pauses off-screen and holds still under reduced motion.
 */
export function RunReplay({ t }: { t: Replay }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { margin: "-80px" });
  const still = useReducedMotion() ?? false;
  const phase = usePhase(inView, still);
  const state = (start: number, end: number) =>
    phase >= end ? "passed" : phase >= start ? "running" : "waiting";

  return (
    <MotionConfig reducedMotion="user">
      <div
        ref={ref}
        role="img"
        aria-label={`${t.label}: ${t.verdict}. ${t.verdictFacts}`}
        className="overflow-hidden rounded-xl bg-panel shadow-frame"
      >
        <div className="flex h-9 items-center gap-2 border-b border-line bg-canvas px-4">
          <Glyph status={phase >= 6 ? "failed" : "running"} />
          <span className="text-xs font-medium text-ink-2">{t.label}</span>
          <span className="ms-auto font-mono text-xs text-ink-4">run-01a1d1…</span>
        </div>
        <div className="grid gap-5 p-5 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <ol className="flex flex-col">
            <Step label={t.queue} state={state(0, 1)} />
            <Step
              label={phase >= 2 ? t.gpuDone : t.gpu}
              state={state(1, 2)}
              extra={phase >= 2 ? t.gpuTime : undefined}
            />
            <Step
              label={t.extract}
              state={state(2, 3)}
              extra={phase >= 3 ? t.extractTime : undefined}
            />
            <Step label={t.rules} state={state(3, 4)} />
            <Step label={t.save} state={state(4, 5)} />
            <AnimatePresence initial={false}>
              {phase === 1 ? (
                <motion.li
                  key="gpu"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25, ease }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 flex items-center gap-3 rounded-lg bg-accent-wash p-3">
                    <div className="flex items-end gap-0.5" aria-hidden>
                      {Array.from({ length: 8 }, (_, i) => i).map((i) => (
                        <motion.span
                          key={i}
                          className="w-1 rounded-full bg-accent"
                          animate={{ height: [4, 14, 4] }}
                          transition={{
                            duration: 1,
                            repeat: Number.POSITIVE_INFINITY,
                            delay: i * 0.08,
                          }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-ink-2">{t.gpuHint}</span>
                  </div>
                </motion.li>
              ) : null}
            </AnimatePresence>
          </ol>

          <div className="min-h-[214px]">
            <AnimatePresence mode="wait">
              {phase >= 6 ? (
                <motion.div
                  key="verdict"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, transition: { duration: 0.2 } }}
                  transition={{ duration: 0.35, ease }}
                  className="flex flex-col gap-3"
                >
                  <div className="flex items-center gap-2">
                    <Glyph status="failed" className="size-4.5" />
                    <span className="text-lg font-semibold text-ink">{t.verdict}</span>
                  </div>
                  <p className="-mt-2 text-xs text-ink-3">{t.verdictFacts}</p>
                  <ul className="divide-y divide-line overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]">
                    {t.fields.map((field, i) => (
                      <motion.li
                        key={field.key}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.12 + i * 0.07, duration: 0.25 }}
                        className={`grid grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-2.5 px-3 py-2 ${field.ok ? "" : "bg-fail-wash/60"}`}
                      >
                        <Glyph status={field.ok ? "passed" : "failed"} />
                        <span className="truncate font-mono text-xs text-ink-2">{field.key}</span>
                        <span className="text-xs font-medium tabular-nums text-ink">
                          {field.value}
                        </span>
                      </motion.li>
                    ))}
                  </ul>
                  <p className="text-xs text-fail-ink">{t.note}</p>
                </motion.div>
              ) : (
                <motion.div
                  key="pending"
                  exit={{ opacity: 0, transition: { duration: 0.15 } }}
                  className="flex h-full flex-col justify-center gap-2"
                  aria-hidden
                >
                  {[0, 1, 2, 3].map((i) => (
                    <span
                      key={i}
                      className="h-8 rounded-md bg-selected"
                      style={{ opacity: 1 - i * 0.18 }}
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </MotionConfig>
  );
}
