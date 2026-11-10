"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { DialogTitle } from "@/components/ui/dialog";
import { MAIN_NAV_ITEMS } from "@/lib/navigation";

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const tNav = useTranslations("nav");
  const tBar = useTranslations("topbar");
  const go = (href: string) => {
    router.push(href);
    onOpenChange(false);
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <DialogTitle className="sr-only">{tBar("searchPlaceholder")}</DialogTitle>
      <CommandInput placeholder={tBar("searchPlaceholder")} />
      <CommandList>
        <CommandEmpty>{tBar("noResults")}</CommandEmpty>
        <CommandGroup heading={tBar("commandGroups.navigate")}>
          {MAIN_NAV_ITEMS.map((item) => (
            <CommandItem key={item.href} onSelect={() => go(item.href)}>
              {tNav(item.labelKey)}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandGroup heading={tBar("commandGroups.workflows")}>
          <CommandItem onSelect={() => go("/workflows/new")}>{tNav("newWorkflow")}</CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
