"use client";

import { CheckboxIndicator, Checkbox as CheckboxPrimitive } from "@ui-sdk/react/checkbox";
import { Check, Minus } from "lucide-react";
import type * as React from "react";
import { partClass } from "@/lib/utils";

function Checkbox({
  className,
  ...props
}: Omit<React.ComponentProps<typeof CheckboxPrimitive>, "children">) {
  return (
    <CheckboxPrimitive
      className={partClass(
        "inline-flex size-3.5 shrink-0 cursor-pointer items-center justify-center rounded-[4px] bg-field text-on-accent shadow-[inset_0_0_0_1px_var(--line-strong)] outline-none transition-[background-color,box-shadow] duration-100 hover:shadow-[inset_0_0_0_1px_var(--ink-4)] focus-visible:shadow-[0_0_0_2px_var(--focus)] data-checked:bg-accent data-checked:shadow-none data-indeterminate:bg-accent data-indeterminate:shadow-none data-disabled:opacity-45",
        className
      )}
      {...props}
    >
      {(state) => (
        <CheckboxIndicator className="flex transition-[scale,opacity] duration-150 ease-out data-starting-style:scale-50 data-starting-style:opacity-0">
          {state.indeterminate ? (
            <Minus className="size-2.5" strokeWidth={3.5} />
          ) : (
            <Check className="size-2.5" strokeWidth={3.5} />
          )}
        </CheckboxIndicator>
      )}
    </CheckboxPrimitive>
  );
}

export { Checkbox };
