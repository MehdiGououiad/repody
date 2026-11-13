import { cn } from "@/lib/utils";

/** One headline number of a strip (overview, control room): a label, the figure in monospace,
 * a line under it, and an optional chart beside it. */
export function Figure({
  label,
  value,
  tone,
  foot,
  chart,
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
  foot?: React.ReactNode;
  chart?: React.ReactNode;
}) {
  return (
    <div className="flex min-w-0 items-end justify-between gap-3 px-4 py-3.5">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="eyebrow text-ink-3">{label}</span>
        <span
          className={cn(
            "flex items-center gap-2 font-mono text-[24px] font-medium leading-tight tracking-[-0.03em] text-ink tabular-nums",
            tone
          )}
        >
          {value}
        </span>
        {foot ? <span className="truncate text-xs text-ink-4">{foot}</span> : null}
      </div>
      {chart}
    </div>
  );
}
