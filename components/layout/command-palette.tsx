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

interface CommandLink {
  groupKey: "navigate" | "audits" | "workflows";
  labelKey: string;
  fallback: string;
  href: string;
}

const commandItems: CommandLink[] = [
  { groupKey: "navigate", labelKey: "nav.dashboard", fallback: "Dashboard", href: "/dashboard" },
  { groupKey: "navigate", labelKey: "nav.workflows", fallback: "Workflows", href: "/workflows" },
  { groupKey: "navigate", labelKey: "nav.audits", fallback: "Audit Reports", href: "/audits" },
  { groupKey: "navigate", labelKey: "nav.settings", fallback: "Settings", href: "/settings" },
  { groupKey: "workflows", labelKey: "common.newWorkflow", fallback: "New workflow", href: "/workflows/new" },
];

const groupKeys: CommandLink["groupKey"][] = ["navigate", "audits", "workflows"];

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const t = useTranslations();
  const tBar = useTranslations("topbar");

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <DialogTitle className="sr-only">{tBar("searchPlaceholder")}</DialogTitle>
      <CommandInput placeholder={tBar("searchPlaceholder")} />
      <CommandList>
        <CommandEmpty>{tBar("noResults")}</CommandEmpty>
        {groupKeys.map((group) => (
          <CommandGroup key={group} heading={tBar(`commandGroups.${group}`)}>
            {commandItems
              .filter((i) => i.groupKey === group)
              .map((i) => (
                <CommandItem
                  key={i.href}
                  onSelect={() => {
                    router.push(i.href);
                    onOpenChange(false);
                  }}
                >
                  {i.labelKey.startsWith("_inline_") ? i.fallback : t(i.labelKey)}
                </CommandItem>
              ))}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
