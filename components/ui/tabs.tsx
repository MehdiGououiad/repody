"use client";

import { Tabs as TabsPrimitive } from "radix-ui";
import type * as React from "react";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

/** Compact text tabs, the active one on a quiet raised step. Switching is instant. */
function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn("inline-flex items-center gap-0.5 text-ink-3", className)}
      {...props}
    />
  );
}

function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex h-7 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 text-sm font-medium transition-colors duration-100 hover:text-ink disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-selected data-[state=active]:text-ink [&_svg]:size-3.5",
        className
      )}
      {...props}
    />
  );
}

function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn("outline-none", className)} {...props} />;
}

export { Tabs, TabsContent, TabsList, TabsTrigger };
