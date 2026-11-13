"use client";

import {
  Tabs,
  TabsIndicator,
  TabsList as TabsListPrimitive,
  TabsPanel,
  TabsTab as TabsTabPrimitive,
} from "@ui-sdk/react/tabs";
import type * as React from "react";
import { cn, partClass } from "@/lib/utils";

/** A row of tabs with one indicator that glides to the selected tab. */
function TabsList({
  className,
  children,
  variant = "plain",
  ...props
}: Omit<React.ComponentProps<typeof TabsListPrimitive>, "children"> & {
  children: React.ReactNode;
  /** `segmented`: a track with a raised thumb, for a few steps or views. */
  variant?: "plain" | "segmented";
}) {
  return (
    <TabsListPrimitive
      className={partClass(
        cn(
          "relative isolate flex items-center gap-0.5",
          variant === "segmented" && "rounded-lg bg-selected p-0.5"
        ),
        className
      )}
      {...props}
    >
      {children}
      <TabsIndicator
        className={cn(
          "absolute start-0 top-0 -z-10 h-(--active-tab-height) w-(--active-tab-width) translate-x-(--active-tab-left) translate-y-(--active-tab-top) rounded-md transition-[translate,width,height] duration-200 ease-out motion-reduce:transition-none",
          variant === "segmented"
            ? "bg-overlay shadow-[0_0_0_1px_var(--line),0_1px_2px_var(--shadow-color)]"
            : "bg-selected"
        )}
      />
    </TabsListPrimitive>
  );
}

function TabsTab({ className, ...props }: React.ComponentProps<typeof TabsTabPrimitive>) {
  return (
    <TabsTabPrimitive
      className={partClass(
        cn(
          "relative z-0 inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2.5 text-[13px] font-medium text-ink-3 outline-none transition-colors duration-150 hover:text-ink focus-visible:shadow-[0_0_0_2px_var(--focus)] data-selected:text-ink [&_svg]:size-3.5"
        ),
        className
      )}
      {...props}
    />
  );
}

export { Tabs, TabsList, TabsPanel, TabsTab };
