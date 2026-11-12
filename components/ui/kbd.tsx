import type * as React from "react";
import { cn } from "@/lib/utils";

/** A keyboard shortcut as a small keycap. */
export function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      className={cn(
        "inline-flex h-4.5 min-w-4.5 items-center justify-center rounded-sm px-1 font-sans text-2xs font-medium text-ink-3 shadow-[inset_0_0_0_1px_var(--line-strong)]",
        className
      )}
      {...props}
    />
  );
}
