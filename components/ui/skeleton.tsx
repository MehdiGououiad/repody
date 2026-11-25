import { cn } from "@/lib/utils";

/** A placeholder of the content's shape while it loads; a soft, slow fade, never a shimmer. */
function SkeletonRoot({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      aria-hidden
      className={cn("animate-pulse rounded-md bg-selected [animation-duration:1.6s]", className)}
      {...props}
    />
  );
}

/** Rows of a list. */
function Lines({ count = 5, className }: { count?: number; className?: string }) {
  return (
    // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- a live region (ARIA status), not the result of a calculation (<output>).
    <div className={cn("flex flex-col gap-3", className)} role="status" aria-busy="true">
      {Array.from({ length: count }, (_, i) => i).map((i) => (
        <SkeletonRoot key={i} className="h-9" style={{ opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export const Skeleton = Object.assign(SkeletonRoot, { Lines });
