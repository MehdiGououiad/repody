"use client";

import {
  Drawer,
  DrawerBackdrop,
  DrawerContent,
  DrawerTitle,
  DrawerTrigger,
} from "@ui-sdk/react/drawer";
import { Menu } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { buttonVariants } from "@/components/ui/button";
import { BrandMark, SidebarContent } from "./app-sidebar";

/** Phones: a slim bar with the brand, and the same sidebar in a drawer from the start edge. */
export function MobileNav() {
  const t = useTranslations("nav");
  const [open, setOpen] = useState(false);

  return (
    <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line bg-panel px-2 md:hidden">
      <Drawer side="start" open={open} onOpenChange={setOpen}>
        <DrawerTrigger
          aria-label={t("openMenu")}
          className={buttonVariants({ variant: "ghost", size: "icon" })}
        >
          <Menu />
        </DrawerTrigger>
        <DrawerBackdrop className="bg-[oklch(0.15_0_0/0.32)]" />
        <DrawerContent className="h-full w-[264px] bg-canvas shadow-pop">
          <DrawerTitle className="sr-only">{t("main")}</DrawerTitle>
          <SidebarContent onNavigate={() => setOpen(false)} />
        </DrawerContent>
      </Drawer>
      <BrandMark />
    </div>
  );
}
