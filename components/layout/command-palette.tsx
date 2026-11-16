"use client";

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandGroupLabel,
  CommandInput,
  CommandItem,
  CommandItemIcon,
  CommandList,
} from "@ui-sdk/react/command";
import { createDialogController } from "@ui-sdk/react/dialog";
import { Monitor, Moon, Plus, Search, Sun } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useCan, useNavItems } from "@/components/auth/access-context";
import { Dialog, DialogBackdrop, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { popupItem, popupLabel } from "@/components/ui/popup";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { cn } from "@/lib/utils";

const palette = createDialogController();

/** Opens the palette from anywhere (the sidebar's search, ⌘K, /). */
export function openCommandPalette() {
  void palette.open();
}

const item = cn(popupItem, "h-8 data-highlighted:bg-selected");

/** ⌘K: go to any page, workflow or recent run; create a workflow; switch the theme. */
export function CommandPalette() {
  const router = useRouter();
  const tNav = useTranslations("nav");
  const tBar = useTranslations("topbar");
  const tAudits = useTranslations("audits");
  const { setTheme } = useTheme();
  const navItems = useNavItems();
  const canCreate = useCan("workflow:write");
  const workflows = $api.useQuery("get", "/v1/workflows").data?.workflows ?? [];
  const runs =
    $api.useQuery("get", "/v1/audits", { params: { query: { limit: 8, offset: 0 } } }).data
      ?.audits ?? [];

  const actions: Record<string, () => void> = {
    "new-workflow": () => router.push("/workflows/new"),
    "theme-light": () => setTheme("light"),
    "theme-dark": () => setTheme("dark"),
    "theme-system": () => setTheme("system"),
  };

  return (
    <Dialog controller={palette}>
      <DialogBackdrop />
      <DialogContent className="top-[12vh] w-[min(620px,calc(100vw-2rem))]">
        <DialogTitle className="sr-only">{tBar("searchPlaceholder")}</DialogTitle>
        <Command
          onAction={(value) => {
            if (actions[value]) actions[value]();
            else router.push(value);
            palette.close();
          }}
        >
          <div className="flex items-center gap-2.5 border-b border-line px-4">
            <Search className="size-4 shrink-0 text-ink-3" aria-hidden />
            <CommandInput
              aria-label={tBar("searchPlaceholder")}
              placeholder={tBar("searchPlaceholder")}
              className="h-12 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-ink-4"
            />
          </div>
          <CommandEmpty className="px-4 py-8 text-center text-[13px] text-ink-3">
            {tBar("noResults")}
          </CommandEmpty>
          <CommandList className="max-h-[52vh] overflow-y-auto overscroll-contain p-1.5">
            <CommandGroup>
              <CommandGroupLabel className={popupLabel}>
                {tBar("commandGroups.actions")}
              </CommandGroupLabel>
              {canCreate ? (
                <CommandItem value="new-workflow" className={item}>
                  <CommandItemIcon>
                    <Plus />
                  </CommandItemIcon>
                  {tNav("newWorkflow")}
                  <span className="ms-auto text-xs text-ink-4">C</span>
                </CommandItem>
              ) : null}
            </CommandGroup>
            <CommandGroup>
              <CommandGroupLabel className={popupLabel}>
                {tBar("commandGroups.navigate")}
              </CommandGroupLabel>
              {navItems.map(({ href, labelKey, icon: Icon }) => (
                <CommandItem key={href} value={href} keywords={[tNav(labelKey)]} className={item}>
                  <CommandItemIcon>
                    <Icon />
                  </CommandItemIcon>
                  {tNav(labelKey)}
                </CommandItem>
              ))}
            </CommandGroup>
            {workflows.length ? (
              <CommandGroup>
                <CommandGroupLabel className={popupLabel}>
                  {tBar("commandGroups.workflows")}
                </CommandGroupLabel>
                {workflows.map((workflow) => (
                  <CommandItem
                    key={workflow.id}
                    value={`/workflows/${workflow.id}/edit`}
                    keywords={[workflow.name, workflow.id]}
                    className={item}
                  >
                    <StatusGlyph status={workflow.status === "active" ? "live" : "draft"} />
                    {workflow.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}
            {runs.length ? (
              <CommandGroup>
                <CommandGroupLabel className={popupLabel}>
                  {tBar("commandGroups.runs")}
                </CommandGroupLabel>
                {runs.map((audit) => (
                  <CommandItem
                    key={audit.id}
                    value={`/audits/${audit.id}`}
                    keywords={[audit.workflowName, audit.id]}
                    className={item}
                  >
                    <StatusGlyph status={audit.status} label={tAudits(`status.${audit.status}`)} />
                    <span className="truncate">{audit.workflowName}</span>
                    <span className="ms-auto font-mono text-xs text-ink-4">
                      {audit.id.slice(-6)}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}
            <CommandGroup>
              <CommandGroupLabel className={popupLabel}>{tBar("toggleTheme")}</CommandGroupLabel>
              <CommandItem value="theme-light" keywords={[tBar("theme.light")]} className={item}>
                <CommandItemIcon>
                  <Sun />
                </CommandItemIcon>
                {tBar("theme.light")}
              </CommandItem>
              <CommandItem value="theme-dark" keywords={[tBar("theme.dark")]} className={item}>
                <CommandItemIcon>
                  <Moon />
                </CommandItemIcon>
                {tBar("theme.dark")}
              </CommandItem>
              <CommandItem value="theme-system" keywords={[tBar("theme.system")]} className={item}>
                <CommandItemIcon>
                  <Monitor />
                </CommandItemIcon>
                {tBar("theme.system")}
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
