"use client";

import {
  Select,
  SelectContent as SelectContentPrimitive,
  SelectGroup,
  SelectGroupLabel as SelectGroupLabelPrimitive,
  SelectItemIndicator,
  SelectItem as SelectItemPrimitive,
  SelectTrigger as SelectTriggerPrimitive,
  SelectValue,
} from "@ui-sdk/react/select";
import { Check, ChevronsUpDown } from "lucide-react";
import type * as React from "react";
import { cn, partClass } from "@/lib/utils";
import { popupItem, popupLabel, popupSurface } from "./popup";

export const triggerClass =
  "inline-flex h-7 min-w-0 cursor-pointer items-center gap-1.5 rounded-md bg-field px-2 text-[13px] text-ink shadow-[inset_0_0_0_1px_var(--line-strong)] outline-none transition-[box-shadow,background-color] duration-150 hover:bg-hover focus-visible:shadow-[inset_0_0_0_1px_var(--accent),0_0_0_3px_var(--accent-wash)] data-open:bg-hover data-disabled:opacity-45 data-invalid:shadow-[inset_0_0_0_1px_var(--fail)]";

function SelectTrigger({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof SelectTriggerPrimitive>, "children"> & {
  children?: React.ReactNode;
}) {
  return (
    <SelectTriggerPrimitive className={partClass(triggerClass, className)} {...props}>
      <span className="min-w-0 flex-1 truncate text-start">{children ?? <SelectValue />}</span>
      <ChevronsUpDown className="size-3 shrink-0 text-ink-4" aria-hidden />
    </SelectTriggerPrimitive>
  );
}

function SelectContent({
  className,
  ...props
}: React.ComponentProps<typeof SelectContentPrimitive>) {
  return (
    <SelectContentPrimitive
      className={partClass(cn(popupSurface, "min-w-(--anchor-width)"), className)}
      {...props}
    />
  );
}

function SelectItem({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof SelectItemPrimitive>, "children"> & {
  children: React.ReactNode;
}) {
  return (
    <SelectItemPrimitive className={partClass(cn(popupItem, "pe-7"), className)} {...props}>
      {children}
      <SelectItemIndicator className="absolute end-2">
        <Check />
      </SelectItemIndicator>
    </SelectItemPrimitive>
  );
}

function SelectGroupLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectGroupLabelPrimitive>) {
  return <SelectGroupLabelPrimitive className={partClass(popupLabel, className)} {...props} />;
}

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectGroupLabel,
  SelectItem,
  SelectTrigger,
  SelectValue,
};
