"use client";

import {
  Menu,
  MenuCheckboxItem,
  MenuContent as MenuContentPrimitive,
  MenuGroup,
  MenuGroupLabel as MenuGroupLabelPrimitive,
  MenuItemIndicator,
  MenuItem as MenuItemPrimitive,
  MenuRadioGroup,
  MenuRadioItem,
  MenuSeparator as MenuSeparatorPrimitive,
  MenuShortcut as MenuShortcutPrimitive,
  MenuTrigger,
} from "@ui-sdk/react/menu";
import { Check } from "lucide-react";
import type * as React from "react";
import { cn, partClass } from "@/lib/utils";
import { popupItem, popupLabel, popupSeparator, popupSurface } from "./popup";

function MenuContent({ className, ...props }: React.ComponentProps<typeof MenuContentPrimitive>) {
  return <MenuContentPrimitive className={partClass(popupSurface, className)} {...props} />;
}

function MenuItem({
  className,
  danger,
  ...props
}: React.ComponentProps<typeof MenuItemPrimitive> & { danger?: boolean }) {
  return (
    <MenuItemPrimitive
      className={partClass(
        cn(
          popupItem,
          danger &&
            "text-fail-ink data-highlighted:bg-fail-wash data-highlighted:text-fail-ink [&_svg]:text-fail-ink"
        ),
        className
      )}
      {...props}
    />
  );
}

function MenuCheck({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof MenuCheckboxItem>, "children"> & {
  children: React.ReactNode;
}) {
  return (
    <MenuCheckboxItem className={partClass(cn(popupItem, "pe-7"), className)} {...props}>
      {children}
      <MenuItemIndicator className="absolute end-2">
        <Check />
      </MenuItemIndicator>
    </MenuCheckboxItem>
  );
}

function MenuRadio({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof MenuRadioItem>, "children"> & { children: React.ReactNode }) {
  return (
    <MenuRadioItem className={partClass(cn(popupItem, "pe-7"), className)} {...props}>
      {children}
      <MenuItemIndicator className="absolute end-2">
        <Check />
      </MenuItemIndicator>
    </MenuRadioItem>
  );
}

function MenuGroupLabel({
  className,
  ...props
}: React.ComponentProps<typeof MenuGroupLabelPrimitive>) {
  return <MenuGroupLabelPrimitive className={partClass(popupLabel, className)} {...props} />;
}

function MenuSeparator({
  className,
  ...props
}: React.ComponentProps<typeof MenuSeparatorPrimitive>) {
  return <MenuSeparatorPrimitive className={partClass(popupSeparator, className)} {...props} />;
}

function MenuShortcut({ className, ...props }: React.ComponentProps<typeof MenuShortcutPrimitive>) {
  return (
    <MenuShortcutPrimitive
      className={partClass("ms-auto ps-4 text-xs tabular-nums text-ink-4", className)}
      {...props}
    />
  );
}

export {
  Menu,
  MenuCheck,
  MenuContent,
  MenuGroup,
  MenuGroupLabel,
  MenuItem,
  MenuRadio,
  MenuRadioGroup,
  MenuSeparator,
  MenuShortcut,
  MenuTrigger,
};
