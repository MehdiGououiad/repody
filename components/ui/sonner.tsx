"use client";

import { useTheme } from "next-themes";
import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

/** Toasts on the overlay surface, quiet: the status shows in a small icon, not a coloured card. */
export function Toaster(props: ToasterProps) {
  const { resolvedTheme } = useTheme();
  return (
    <SonnerToaster
      theme={(resolvedTheme ?? "system") as ToasterProps["theme"]}
      position="bottom-right"
      duration={4000}
      gap={8}
      toastOptions={{
        classNames: {
          toast:
            "!rounded-lg !border-0 !bg-overlay !text-ink !shadow-pop !text-sm !font-sans !gap-2.5 !px-3.5 !py-3",
          title: "!font-medium",
          description: "!text-ink-3 !text-xs",
          actionButton: "!bg-accent !text-on-accent !rounded-md !text-xs !font-medium",
          cancelButton: "!bg-selected !text-ink-2 !rounded-md !text-xs",
          success: "[&_[data-icon]]:!text-pass",
          error: "[&_[data-icon]]:!text-fail",
          warning: "[&_[data-icon]]:!text-warn",
        },
      }}
      {...props}
    />
  );
}
