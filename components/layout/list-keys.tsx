"use client";

import { useShortcut } from "@ui-sdk/react/shortcuts";
import { useTranslations } from "next-intl";
import { Kbd } from "@/components/ui/kbd";

/** J/K or arrows move through the rows of a list (`data-row` links); Enter follows the link. */
export function useListKeys(scope: React.RefObject<HTMLElement | null>) {
  const t = useTranslations("shell.keys");
  const move = (step: number) => {
    const rows = Array.from(scope.current?.querySelectorAll<HTMLElement>("[data-row]") ?? []);
    if (!rows.length) return;
    const current = rows.indexOf(document.activeElement as HTMLElement);
    const next = rows[Math.min(Math.max(current + step, 0), rows.length - 1)] ?? rows[0];
    next.focus();
    next.scrollIntoView({ block: "nearest" });
  };
  useShortcut("j", () => move(1), { description: t("move") });
  useShortcut("k", () => move(-1), { description: t("move") });
  useShortcut("arrowdown", () => move(1), { description: t("move") });
  useShortcut("arrowup", () => move(-1), { description: t("move") });
}

/** The keys a list answers to, in its footer. */
export function ListKeysHint({ extra }: { extra?: React.ReactNode }) {
  const t = useTranslations("shell.keys");
  return (
    <span className="hidden items-center gap-3 text-xs text-ink-4 lg:flex">
      <span className="flex items-center gap-1">
        <Kbd>J</Kbd>
        <Kbd>K</Kbd>
        {t("move")}
      </span>
      <span className="flex items-center gap-1">
        <Kbd>↵</Kbd>
        {t("open")}
      </span>
      <span className="flex items-center gap-1">
        <Kbd>/</Kbd>
        {t("search")}
      </span>
      {extra}
    </span>
  );
}
