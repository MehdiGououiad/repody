"use client";

import { Monitor, Moon, Plus, Sun } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { MAIN_NAV_ITEMS } from "@/lib/navigation";

/** ⌘K: go to any page, workflow or recent run; create a workflow; switch the theme. */
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
  const tAudits = useTranslations("audits");
  const { setTheme } = useTheme();
  // Already cached on most pages; fetched once here otherwise.
  const workflows = $api.useQuery("get", "/v1/workflows").data?.workflows ?? [];
  const runs =
    $api.useQuery("get", "/v1/audits", { params: { query: { limit: 8, offset: 0 } } }).data
      ?.audits ?? [];
  const run = (action: () => void) => {
    action();
    onOpenChange(false);
  };
  const go = (href: string) => run(() => router.push(href));

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title={tBar("searchPlaceholder")}>
      <CommandInput placeholder={tBar("searchPlaceholder")} />
      <CommandList>
        <CommandEmpty>{tBar("noResults")}</CommandEmpty>
        <CommandGroup heading={tBar("commandGroups.actions")}>
          <CommandItem onSelect={() => go("/workflows/new")}>
            <Plus />
            {tNav("newWorkflow")}
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading={tBar("commandGroups.navigate")}>
          {MAIN_NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => (
            <CommandItem key={href} onSelect={() => go(href)}>
              <Icon />
              {tNav(labelKey)}
            </CommandItem>
          ))}
        </CommandGroup>
        {workflows.length ? (
          <CommandGroup heading={tBar("commandGroups.workflows")}>
            {workflows.map((workflow) => (
              <CommandItem
                key={workflow.id}
                value={`workflow ${workflow.name} ${workflow.id}`}
                onSelect={() => go(`/workflows/${workflow.id}/edit`)}
              >
                <StatusGlyph status={workflow.status === "active" ? "live" : "draft"} />
                {workflow.name}
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}
        {runs.length ? (
          <CommandGroup heading={tBar("commandGroups.runs")}>
            {runs.map((audit) => (
              <CommandItem
                key={audit.id}
                value={`run ${audit.workflowName} ${audit.id}`}
                onSelect={() => go(`/audits/${audit.id}`)}
              >
                <StatusGlyph status={audit.status} label={tAudits(`status.${audit.status}`)} />
                <span className="truncate">{audit.workflowName}</span>
                <span className="ms-auto font-mono text-xs text-ink-4">{audit.id.slice(-8)}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}
        <CommandGroup heading={tBar("toggleTheme")}>
          <CommandItem onSelect={() => run(() => setTheme("light"))}>
            <Sun />
            {tBar("theme.light")}
          </CommandItem>
          <CommandItem onSelect={() => run(() => setTheme("dark"))}>
            <Moon />
            {tBar("theme.dark")}
          </CommandItem>
          <CommandItem onSelect={() => run(() => setTheme("system"))}>
            <Monitor />
            {tBar("theme.system")}
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
