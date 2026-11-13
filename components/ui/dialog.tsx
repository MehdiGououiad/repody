"use client";

import {
  Dialog,
  DialogBackdrop as DialogBackdropPrimitive,
  DialogClose,
  DialogContent as DialogContentPrimitive,
  DialogDescription as DialogDescriptionPrimitive,
  DialogTitle as DialogTitlePrimitive,
  DialogTrigger,
} from "@ui-sdk/react/dialog";
import type * as React from "react";
import { cn, partClass } from "@/lib/utils";

export const backdropClass =
  "fixed inset-0 z-50 bg-[oklch(0.15_0_0/0.32)] transition-opacity duration-200 data-starting-style:opacity-0 data-ending-style:opacity-0 data-ending-style:duration-120 motion-reduce:transition-none";

export const dialogSurface =
  "fixed start-1/2 top-[14vh] z-50 flex max-h-[76vh] w-[min(560px,calc(100vw-2rem))] -translate-x-1/2 flex-col overflow-hidden rounded-xl bg-overlay text-ink shadow-pop outline-none transition-[opacity,scale] duration-200 ease-out data-starting-style:scale-[0.96] data-starting-style:opacity-0 data-ending-style:scale-[0.97] data-ending-style:opacity-0 data-ending-style:duration-120 motion-reduce:transition-none rtl:translate-x-1/2";

function DialogBackdrop({
  className,
  ...props
}: React.ComponentProps<typeof DialogBackdropPrimitive>) {
  return <DialogBackdropPrimitive className={partClass(backdropClass, className)} {...props} />;
}

function DialogContent({
  className,
  size = "md",
  ...props
}: React.ComponentProps<typeof DialogContentPrimitive> & { size?: "sm" | "md" | "lg" }) {
  return (
    <DialogContentPrimitive
      className={partClass(
        cn(
          dialogSurface,
          size === "sm" && "w-[min(420px,calc(100vw-2rem))]",
          size === "lg" && "w-[min(760px,calc(100vw-2rem))]"
        ),
        className
      )}
      {...props}
    />
  );
}

function DialogTitle({ className, ...props }: React.ComponentProps<typeof DialogTitlePrimitive>) {
  return (
    <DialogTitlePrimitive
      className={partClass("text-[15px] font-semibold text-ink", className)}
      {...props}
    />
  );
}

function DialogDescription({
  className,
  ...props
}: React.ComponentProps<typeof DialogDescriptionPrimitive>) {
  return (
    <DialogDescriptionPrimitive
      className={partClass("mt-1 text-[13px] text-ink-3", className)}
      {...props}
    />
  );
}

/** Title block, body and footer: the three zones every dialog uses. */
function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("px-5 pt-4 pb-3", className)} {...props} />;
}

function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("min-h-0 flex-1 overflow-y-auto px-5 pb-4", className)} {...props} />;
}

function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-2 border-t border-line bg-raised px-5 py-3",
        className
      )}
      {...props}
    />
  );
}

export {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
};
