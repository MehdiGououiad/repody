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

type Group = "navigate" | "workflows";

const commands: {
  group: Group;
  label: Parameters<ReturnType<typeof useTranslations>>[0];
  href: string;
}[] = [
  { group: "navigate", label: "nav.dashboard", href: "/dashboard" },
  { group: "navigate", label: "nav.workflows", href: "/workflows" },
  { group: "navigate", label: "nav.audits", href: "/audits" },
  { group: "navigate", label: "nav.settings", href: "/settings" },
  { group: "workflows", label: "common.newWorkflow", href: "/workflows/new" },
];

const groups: Group[] = ["navigate", "workflows"];

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
        {groups.map((group) => (
          <CommandGroup key={group} heading={tBar(`commandGroups.${group}`)}>
            {commands
              .filter((command) => command.group === group)
              .map((command) => (
                <CommandItem
                  key={command.href}
                  onSelect={() => {
                    router.push(command.href);
                    onOpenChange(false);
                  }}
                >
                  {t(command.label)}
                </CommandItem>
              ))}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
