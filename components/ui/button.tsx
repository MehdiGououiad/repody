"use client";

import { Button as ButtonPrimitive } from "@ui-sdk/react/button";
import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";
import { partClass } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer select-none items-center justify-center gap-1.5 whitespace-nowrap rounded-md font-medium outline-none transition-[background-color,color,box-shadow,scale] duration-150 ease-out active:scale-[0.97] focus-visible:shadow-[0_0_0_2px_var(--focus)] data-disabled:cursor-not-allowed data-disabled:opacity-45 data-pending:cursor-progress [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-on-accent shadow-[inset_0_1px_0_oklch(1_0_0/0.14),0_1px_2px_var(--shadow-color)] hover:bg-accent-hover",
        secondary:
          "bg-raised text-ink shadow-[0_0_0_1px_var(--line-strong),0_1px_2px_var(--shadow-color)] hover:bg-hover",
        ghost: "text-ink-2 hover:bg-hover hover:text-ink data-open:bg-selected data-open:text-ink",
        danger: "bg-fail text-white hover:opacity-90",
      },
      size: {
        xs: "h-6 px-2 text-xs [&_svg]:size-3",
        sm: "h-7 px-2.5 text-[13px] [&_svg]:size-3.5",
        md: "h-8 px-3 text-[13px] [&_svg]:size-3.5",
        "icon-xs": "size-6 [&_svg]:size-3.5",
        "icon-sm": "size-7 [&_svg]:size-3.5",
        icon: "size-8 [&_svg]:size-4",
      },
    },
    defaultVariants: { variant: "secondary", size: "sm" },
  }
);

type ButtonProps = React.ComponentProps<typeof ButtonPrimitive> &
  VariantProps<typeof buttonVariants>;

/** One primary action per view; everything else is secondary or ghost. Links pass `render`. */
function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <ButtonPrimitive
      className={partClass(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { Button, buttonVariants };
