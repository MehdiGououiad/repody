import { cn } from "@/lib/utils";

export function SectionHeading({
  title,
  description,
  eyebrow,
  className,
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      {eyebrow ? (
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-blue">
          {eyebrow}
        </p>
      ) : null}
      <h2 className="font-display text-xl md:text-2xl font-semibold text-on-surface tracking-tight leading-tight">
        {title}
      </h2>
      {description ? (
        <p className="text-sm text-on-surface-variant leading-relaxed max-w-2xl">{description}</p>
      ) : null}
    </div>
  );
}
