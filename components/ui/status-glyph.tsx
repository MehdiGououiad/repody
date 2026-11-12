import { cn } from "@/lib/utils";

export type GlyphStatus =
  | "waiting"
  | "running"
  | "passed"
  | "warning"
  | "failed"
  | "skipped"
  | "draft"
  | "live";

const TONE: Record<GlyphStatus, string> = {
  waiting: "text-ink-4",
  running: "text-accent",
  passed: "text-pass",
  warning: "text-warn",
  failed: "text-fail",
  skipped: "text-ink-4",
  draft: "text-ink-4",
  live: "text-pass",
};

/**
 * The one status mark of the product, in a fixed 14px box: a ring while waiting, a turning arc
 * while running, a filled circle with a tick, an exclamation or a cross once judged. Colour is
 * never the only cue: each state has its own shape, and the label says it in words.
 */
export function StatusGlyph({
  status,
  label,
  className,
}: {
  status: GlyphStatus;
  label?: string;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 14 14"
      className={cn("size-3.5 shrink-0", TONE[status], className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {label ? <title>{label}</title> : null}
      {status === "waiting" || status === "draft" ? (
        <circle
          cx="7"
          cy="7"
          r="5.75"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeDasharray={status === "draft" ? "2.2 2" : undefined}
        />
      ) : null}
      {status === "skipped" ? (
        <>
          <circle cx="7" cy="7" r="5.75" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M4.5 7h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </>
      ) : null}
      {status === "running" ? (
        <>
          <circle
            cx="7"
            cy="7"
            r="5.75"
            fill="none"
            stroke="currentColor"
            strokeOpacity="0.25"
            strokeWidth="1.5"
          />
          <path
            d="M7 1.25a5.75 5.75 0 0 1 5.75 5.75"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            className="origin-center animate-spin [animation-duration:900ms] motion-reduce:animate-none"
          />
        </>
      ) : null}
      {status === "live" ? (
        <>
          <circle
            cx="7"
            cy="7"
            r="5.75"
            fill="none"
            stroke="currentColor"
            strokeOpacity="0.3"
            strokeWidth="1.5"
          />
          <circle cx="7" cy="7" r="3" fill="currentColor" />
        </>
      ) : null}
      {status === "passed" || status === "warning" || status === "failed" ? (
        <circle cx="7" cy="7" r="6.5" fill="currentColor" />
      ) : null}
      {status === "passed" ? (
        <path
          d="M4.4 7.2 6.2 9l3.4-3.8"
          fill="none"
          stroke="var(--panel)"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : null}
      {status === "warning" ? (
        <path
          d="M7 3.9v3.6M7 9.9v.1"
          fill="none"
          stroke="var(--panel)"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      ) : null}
      {status === "failed" ? (
        <path
          d="M5 5l4 4M9 5 5 9"
          fill="none"
          stroke="var(--panel)"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      ) : null}
    </svg>
  );
}
