"use client";

import {
  SegmentedControlIndicator,
  SegmentedControlItem,
  SegmentedControl as SegmentedControlPrimitive,
} from "@ui-sdk/react/segmented-control";
import type * as React from "react";
import { partClass } from "@/lib/utils";

/** A compact row of choices with a sliding thumb. */
function SegmentedControl({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof SegmentedControlPrimitive>, "children"> & {
  children: React.ReactNode;
}) {
  return (
    <SegmentedControlPrimitive
      className={partClass(
        "relative isolate inline-flex h-7 items-center rounded-md bg-selected p-0.5",
        className,
      )}
      {...props}
    >
      <SegmentedControlIndicator className="absolute -z-10 h-(--segmented-control-indicator-height) w-(--segmented-control-indicator-width) translate-x-(--segmented-control-indicator-left) rounded-[5px] bg-overlay shadow-[0_0_0_1px_var(--line),0_1px_2px_var(--shadow-color)] transition-[translate,width] duration-200 ease-out motion-reduce:transition-none" />
      {children}
    </SegmentedControlPrimitive>
  );
}

function SegmentedControlOption({
  className,
  ...props
}: React.ComponentProps<typeof SegmentedControlItem>) {
  return (
    <SegmentedControlItem
      className={partClass(
        "inline-flex h-6 cursor-pointer items-center gap-1.5 rounded-[5px] px-2.5 text-xs font-medium text-ink-3 outline-none transition-colors duration-150 hover:text-ink focus-visible:shadow-[0_0_0_2px_var(--focus)] data-checked:text-ink [&_svg]:size-3.5",
        className,
      )}
      {...props}
    />
  );
}

export { SegmentedControl, SegmentedControlOption };
