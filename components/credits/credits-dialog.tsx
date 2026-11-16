"use client";

import { ArrowUpRight, MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";
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
import type { CreditsContact } from "@/lib/credits/contact";
import { creditsDialog } from "@/lib/credits/dialog";

/** "Contact us for credits": opened when the API refuses a run its account cannot pay (402). */
export function CreditsDialog({ contact }: Readonly<{ contact: CreditsContact }>) {
  const t = useTranslations("credits");
  return (
    <Dialog controller={creditsDialog}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("hint")}</DialogDescription>
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
          <DialogClose render={<Button variant="ghost" />}>{t("close")}</DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
