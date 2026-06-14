import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
  eyebrow?: string;
}

export function PageHeader({
  title,
  description,
  actions,
  className,
  eyebrow,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col md:flex-row md:items-end justify-between gap-4 mb-2",
        className
      )}
    >
      <div className="space-y-2 max-w-2xl">
        {eyebrow ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent-blue">
            {eyebrow}
          </p>
        ) : null}
        <div className="accent-rule" aria-hidden />
        <h1 className="font-display text-3xl md:text-[2.35rem] font-semibold tracking-tight text-on-surface leading-[1.1] text-balance">
          {title}
        </h1>
        {description ? (
          <p className="text-sm text-on-surface-variant leading-relaxed max-w-xl">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      ) : null}
    </div>
  );
}
