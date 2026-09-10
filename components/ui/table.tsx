import type * as React from "react";
import { cn } from "@/lib/utils";

function Table({ className, ref, ...props }: React.ComponentProps<"table">) {
  return (
    <div className="relative w-full overflow-auto">
      <table
        ref={ref}
        className={cn("w-full caption-bottom text-sm border-collapse", className)}
        {...props}
      />
    </div>
  );
}

function TableHeader({ className, ref, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      ref={ref}
      className={cn(
        "[&_tr]:border-b border-border bg-surface-container-low text-xs font-semibold uppercase tracking-wider text-on-surface-variant",
        className
      )}
      {...props}
    />
  );
}

function TableBody({ className, ref, ...props }: React.ComponentProps<"tbody">) {
  return <tbody ref={ref} className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}

function TableRow({ className, ref, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      ref={ref}
      className={cn(
        "border-b border-border transition-colors hover:bg-surface-bright data-[state=selected]:bg-muted",
        className
      )}
      {...props}
    />
  );
}

function TableHead({ className, ref, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      ref={ref}
      className={cn(
        "h-10 px-4 text-left align-middle font-semibold text-on-surface-variant",
        className
      )}
      {...props}
    />
  );
}

function TableCell({ className, ref, ...props }: React.ComponentProps<"td">) {
  return <td ref={ref} className={cn("p-4 align-middle", className)} {...props} />;
}

export { Table, TableBody, TableCell, TableHead, TableHeader, TableRow };
