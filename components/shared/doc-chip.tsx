import { docColor } from "@/lib/doc-color";
import { cn } from "@/lib/utils";

/** A document's name in its colour: a dot and the name, or a wash chip. */
export function DocChip({
  index,
  children,
  variant = "dot",
  className,
}: {
  index: number;
  children: React.ReactNode;
  variant?: "dot" | "chip";
  className?: string;
}) {
  const color = docColor(index);
  if (variant === "chip") {
    return (
      <span
        className={cn(
          "inline-flex h-5 max-w-full items-center gap-1.5 rounded-sm px-1.5 text-xs font-medium",
          color.wash,
          color.ink,
          className
        )}
      >
        <span className={cn("size-1.5 shrink-0 rounded-full", color.dot)} aria-hidden />
        <span className="truncate">{children}</span>
      </span>
    );
  }
  return (
    <span className={cn("inline-flex min-w-0 items-center gap-1.5", className)}>
      <span className={cn("size-2 shrink-0 rounded-[3px]", color.dot)} aria-hidden />
      <span className="truncate">{children}</span>
    </span>
  );
}
