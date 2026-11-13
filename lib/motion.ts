/** The product's motion presets (`.interface-design/system.md`): quick, out-eased, never bouncy. */
export const EASE_OUT = [0.23, 1, 0.32, 1] as const;

/** Rows entering a list: a short rise, staggered, only for the first rows on screen. */
export const rowEnter = (index: number) => ({
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.18, ease: EASE_OUT, delay: Math.min(index, 8) * 0.02 },
});
