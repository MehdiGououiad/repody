import { cn } from "@/lib/utils";

/** The title of a builder step: one quiet heading and a one-line hint. */
export function SectionHeading({
  title,
  description,
  className,
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      {description ? <p className="max-w-2xl text-sm text-ink-3">{description}</p> : null}
    </div>
  );
}
