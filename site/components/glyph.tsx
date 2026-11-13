/** The product's status glyph (components/ui/status-glyph.tsx), the signature of both. */
export type GlyphStatus = "waiting" | "running" | "passed" | "warning" | "failed" | "live";

const TONE: Record<GlyphStatus, string> = {
  waiting: "text-ink-4",
  running: "text-accent",
  passed: "text-pass",
  warning: "text-warn",
  failed: "text-fail",
  live: "text-pass",
};

export function Glyph({ status, className = "" }: { status: GlyphStatus; className?: string }) {
  const filled = status === "passed" || status === "warning" || status === "failed";
  return (
    <svg
      viewBox="0 0 14 14"
      className={`size-3.5 shrink-0 ${TONE[status]} ${className}`}
      aria-hidden
    >
      {status === "waiting" ? (
        <circle cx="7" cy="7" r="5.75" fill="none" stroke="currentColor" strokeWidth="1.5" />
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
      {filled ? <circle cx="7" cy="7" r="6.5" fill="currentColor" /> : null}
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
