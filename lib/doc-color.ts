/**
 * Each document of a workflow keeps one colour (`--doc-1..8` from the theme) everywhere it shows:
 * builder, rules, runs and report. Written out in full so Tailwind sees every class.
 */
const PALETTE = [
  { dot: "bg-doc-1", ink: "text-doc-1-ink", wash: "bg-doc-1-wash", ring: "ring-doc-1" },
  { dot: "bg-doc-2", ink: "text-doc-2-ink", wash: "bg-doc-2-wash", ring: "ring-doc-2" },
  { dot: "bg-doc-3", ink: "text-doc-3-ink", wash: "bg-doc-3-wash", ring: "ring-doc-3" },
  { dot: "bg-doc-4", ink: "text-doc-4-ink", wash: "bg-doc-4-wash", ring: "ring-doc-4" },
  { dot: "bg-doc-5", ink: "text-doc-5-ink", wash: "bg-doc-5-wash", ring: "ring-doc-5" },
  { dot: "bg-doc-6", ink: "text-doc-6-ink", wash: "bg-doc-6-wash", ring: "ring-doc-6" },
  { dot: "bg-doc-7", ink: "text-doc-7-ink", wash: "bg-doc-7-wash", ring: "ring-doc-7" },
  { dot: "bg-doc-8", ink: "text-doc-8-ink", wash: "bg-doc-8-wash", ring: "ring-doc-8" },
] as const;

export type DocColor = (typeof PALETTE)[number];

export function docColor(index: number): DocColor {
  return PALETTE[((index % PALETTE.length) + PALETTE.length) % PALETTE.length];
}
