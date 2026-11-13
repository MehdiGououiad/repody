"use client";

import {
  TooltipContent,
  Tooltip as TooltipRoot,
  TooltipShortcut,
  TooltipTrigger,
} from "@ui-sdk/react/tooltip";
import type * as React from "react";

/** A short hint, with the shortcut that does the same thing. Tooltips in a row open at once. */
export function Tooltip({
  label,
  shortcut,
  children,
  side = "bottom",
}: {
  label: string;
  shortcut?: string;
  children: React.ReactElement<Record<string, unknown>>;
  side?: "top" | "bottom" | "left" | "right";
}) {
  return (
    <TooltipRoot delay={400}>
      <TooltipTrigger render={children} />
      <TooltipContent
        side={side}
        className="z-[70] flex origin-(--transform-origin) items-center gap-2 rounded-md bg-ink px-2 py-1 text-xs font-medium text-panel shadow-pop transition-[opacity,scale] duration-120 data-instant:transition-none data-starting-style:scale-95 data-starting-style:opacity-0 data-ending-style:opacity-0 motion-reduce:transition-none"
      >
        {label}
        {shortcut ? (
          <TooltipShortcut className="text-2xs tabular-nums opacity-60">{shortcut}</TooltipShortcut>
        ) : null}
      </TooltipContent>
    </TooltipRoot>
  );
}
