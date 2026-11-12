"use client";

import { Check, Minus } from "lucide-react";
import { Checkbox as CheckboxPrimitive } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

function Checkbox({ className, ...props }: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      className={cn(
        "peer relative flex size-3.5 shrink-0 cursor-pointer items-center justify-center rounded-[4px] bg-field shadow-[inset_0_0_0_1px_var(--ink-4)] transition-[background-color,box-shadow] duration-100 before:absolute before:-inset-2 data-[state=checked]:bg-accent data-[state=indeterminate]:bg-accent data-[state=checked]:shadow-none data-[state=indeterminate]:shadow-none disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="text-on-accent">
        {props.checked === "indeterminate" ? (
          <Minus className="size-3" strokeWidth={3} />
        ) : (
          <Check className="size-3" strokeWidth={3} />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

export { Checkbox };
