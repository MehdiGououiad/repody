"use client";

import { ArrowUpRight, MessageCircle, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, useContext } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { PlaygroundContact } from "@/lib/playground/config";
import { creditsDialog, openCredits } from "@/lib/playground/credits";

const PlaygroundContext = createContext<PlaygroundContact | null>(null);

/** The playground's contact details, or null outside the playground (demo mode). */
export function usePlayground(): PlaygroundContact | null {
  return useContext(PlaygroundContext);
}

/** Demo mode for the app below it: the banner, and the credits dialog the gated actions open. */
export function PlaygroundProvider({
  contact,
  children,
}: {
  contact: PlaygroundContact | null;
  children: React.ReactNode;
}) {
  return (
    <PlaygroundContext value={contact}>
      {children}
      {contact ? <CreditsDialog contact={contact} /> : null}
    </PlaygroundContext>
  );
}

/** One line above the page: what the playground is, and how to go further. */
export function PlaygroundBanner() {
  const t = useTranslations("playground");
  if (!usePlayground()) return null;
  return (
    <div className="flex h-9 shrink-0 items-center gap-3 border-b border-line bg-accent-wash px-4 text-[13px] text-accent-ink">
      <span className="flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide uppercase">
        <Sparkles className="size-3.5" aria-hidden />
        {t("label")}
      </span>
      <span className="hidden min-w-0 truncate text-ink-2 sm:block">{t("banner")}</span>
      <Button variant="primary" size="xs" className="ms-auto" onClick={openCredits}>
        {t("getCredits")}
      </Button>
    </div>
  );
}

function CreditsDialog({ contact }: { contact: PlaygroundContact }) {
  const t = useTranslations("playground");
  return (
    <Dialog controller={creditsDialog}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{t("creditsTitle")}</DialogTitle>
          <DialogDescription>{t("creditsHint")}</DialogDescription>
        </DialogHeader>
        <DialogBody className="flex flex-col gap-2">
          <Button
            variant="primary"
            className="justify-between"
            render={<a href={contact.contactUrl} target="_blank" rel="noopener" />}
          >
            {t("contactForm")}
            <ArrowUpRight />
          </Button>
          {contact.whatsapp ? (
            <Button
              variant="secondary"
              className="justify-between"
              render={
                <a href={`https://wa.me/${contact.whatsapp}`} target="_blank" rel="noopener" />
              }
            >
              <span className="flex items-center gap-2">
                <MessageCircle />
                {t("whatsapp")}
              </span>
              <ArrowUpRight />
            </Button>
          ) : null}
        </DialogBody>
        <DialogFooter>
          <DialogClose render={<Button variant="ghost" />}>{t("keepExploring")}</DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
