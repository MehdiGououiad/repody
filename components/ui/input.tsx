import type * as React from "react";
import { cn } from "@/lib/utils";

/** Fields are inset: a slightly darker fill and a hairline, the accent ring only on focus. */
export const fieldClassName =
  "rounded-md bg-field text-sm text-ink shadow-[inset_0_0_0_1px_var(--line-strong)] outline-none transition-[box-shadow] duration-100 placeholder:text-ink-4 hover:shadow-[inset_0_0_0_1px_var(--ink-4)] focus-visible:shadow-[inset_0_0_0_1px_var(--accent),0_0_0_3px_var(--accent-wash)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:shadow-[inset_0_0_0_1px_var(--fail)]";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        fieldClassName,
        "flex h-8 w-full min-w-0 px-2.5 file:me-2 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-ink",
        className
      )}
      {...props}
    />
  );
}

export { Input };
