"use client";

import {
  AlertDialog,
  AlertDialogBackdrop,
  AlertDialogClose,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  createConfirm,
} from "@ui-sdk/react/alert-dialog";
import { Toast, ToastDescription, ToastRegion, ToastTitle } from "@ui-sdk/react/toast";
import { CircleAlert, CircleCheck, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "./button";
import { backdropClass, dialogSurface } from "./dialog";

type ConfirmQuestion = {
  title: string;
  description?: string;
  confirmLabel: string;
  cancelLabel: string;
  danger?: boolean;
};

/** `if (await confirmAction({ … })) remove()`: one question at a time, from any event handler. */
export const confirmAction = createConfirm<ConfirmQuestion>();

/** The page's toasts and questions; rendered once in the app layout. */
export function Overlays() {
  return (
    <>
      <ToastRegion className="fixed end-4 bottom-4 z-[60] w-[360px] [height:var(--toast-front-height)] data-expanded:[height:calc(var(--toast-stack-height)+(var(--toast-count)-1)*8px)]">
        {() => (
          <Toast className="group absolute inset-x-0 bottom-0 z-[calc(100-var(--toast-index))] flex [height:var(--toast-height)] select-none items-start gap-2.5 overflow-hidden rounded-lg bg-overlay px-3.5 py-3 text-[13px] text-ink shadow-pop transition-[translate,scale,opacity,height] duration-300 ease-out [scale:calc(1-var(--toast-index)*0.04)] [translate:var(--toast-swipe-x,0px)_calc(var(--toast-index)*-8px+var(--toast-swipe-y,0px))] data-expanded:[scale:1] data-expanded:[translate:0_calc(var(--toast-offset)*-1-var(--toast-index)*8px)] data-ending-style:opacity-0 data-starting-style:[translate:0_100%] data-starting-style:opacity-0 data-swiping:transition-none [&:not([data-front]):not([data-expanded])>*]:opacity-0">
            <CircleCheck
              data-show="success"
              className="mt-px size-4 shrink-0 text-pass"
              aria-hidden
            />
            <CircleAlert
              data-show="error"
              className="mt-px size-4 shrink-0 text-fail"
              aria-hidden
            />
            <Info data-show="info" className="mt-px size-4 shrink-0 text-accent" aria-hidden />
            <div className="min-w-0">
              <ToastTitle className="font-medium" />
              <ToastDescription className="mt-0.5 text-ink-3" />
            </div>
          </Toast>
        )}
      </ToastRegion>

      <AlertDialog controller={confirmAction.controller}>
        <AlertDialogBackdrop className={backdropClass} />
        <AlertDialogContent<ConfirmQuestion>
          className={cn(dialogSurface, "w-[min(420px,calc(100vw-2rem))]")}
        >
          {(state) => (
            <>
              <div className="px-5 pt-4 pb-4">
                <AlertDialogTitle className="text-[15px] font-semibold">
                  {state.payload?.title}
                </AlertDialogTitle>
                {state.payload?.description ? (
                  <AlertDialogDescription className="mt-1.5 text-[13px] text-ink-3">
                    {state.payload.description}
                  </AlertDialogDescription>
                ) : null}
              </div>
              <div className="flex justify-end gap-2 border-t border-line bg-raised px-5 py-3">
                <AlertDialogClose className={buttonVariants({ variant: "ghost" })}>
                  {state.payload?.cancelLabel}
                </AlertDialogClose>
                <AlertDialogClose
                  value="confirm"
                  className={buttonVariants({
                    variant: state.payload?.danger ? "danger" : "primary",
                  })}
                >
                  {state.payload?.confirmLabel}
                </AlertDialogClose>
              </div>
            </>
          )}
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
