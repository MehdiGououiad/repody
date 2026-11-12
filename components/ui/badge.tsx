import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";
import { cn } from "@/lib/utils";

/** Quiet labels: a tinted wash with ink of the same hue, never a loud filled pill. */
const badgeVariants = cva(
  "inline-flex h-5 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-sm px-1.5 text-xs font-medium tabular-nums [&_svg]:size-3",
  {
    variants: {
      variant: {
        default: "bg-selected text-ink-2",
        secondary: "bg-selected text-ink-2",
        outline: "text-ink-2 shadow-[inset_0_0_0_1px_var(--line-strong)]",
        accent: "bg-accent-wash text-accent-ink",
        info: "bg-accent-wash text-accent-ink",
        success: "bg-pass-wash text-pass-ink",
        warning: "bg-warn-wash text-warn-ink",
        danger: "bg-fail-wash text-fail-ink",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

const DOT: Record<string, string> = {
  success: "bg-pass",
  warning: "bg-warn",
  danger: "bg-fail",
  info: "bg-accent",
  accent: "bg-accent",
};

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  withDot?: boolean;
}

function Badge({ className, variant, withDot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {withDot ? (
        <span className={cn("size-1.5 rounded-full", DOT[variant ?? ""] ?? "bg-ink-3")} />
      ) : null}
      {children}
    </span>
  );
}

export { Badge, badgeVariants };
