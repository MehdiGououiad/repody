import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

/** One primary action per view (accent); everything else is secondary or ghost. */
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer select-none items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-sm font-medium transition-[background-color,color,box-shadow,scale] duration-150 ease-out enabled:active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-45 [&_svg]:pointer-events-none [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-accent text-on-accent hover:bg-accent-hover",
        secondary: "bg-raised text-ink shadow-[0_0_0_1px_var(--line-strong)] hover:bg-hover",
        outline: "bg-raised text-ink shadow-[0_0_0_1px_var(--line-strong)] hover:bg-hover",
        ghost: "text-ink-2 hover:bg-hover hover:text-ink",
        destructive: "bg-fail text-white hover:opacity-90",
        danger: "bg-fail text-white hover:opacity-90",
        success: "bg-pass text-white hover:opacity-90",
        link: "h-auto px-0 text-accent-ink underline-offset-4 hover:underline enabled:active:scale-100",
      },
      size: {
        default: "h-8 px-3",
        md: "h-8 px-3",
        sm: "h-7 px-2.5 text-xs",
        lg: "h-9 px-4",
        icon: "size-8",
        "icon-sm": "size-7",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  ref?: React.Ref<HTMLButtonElement>;
}

function Button({ className, variant, size, asChild = false, ref, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
}

export { Button, buttonVariants };
