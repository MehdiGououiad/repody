"use client";

import { createDialogController } from "@ui-sdk/react/dialog";
import { shortcuts, useShortcut } from "@ui-sdk/react/shortcuts";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { useCan } from "@/components/auth/access-context";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/kbd";
import { CommandPalette, openCommandPalette } from "./command-palette";

const help = createDialogController();
const SEQUENCE_MS = 1200;
const GO_KEYS = {
  o: "/dashboard",
  c: "/operations",
  w: "/workflows",
  r: "/audits",
  s: "/settings",
} as const;
const GO_LABELS = {
  o: "dashboard",
  c: "operations",
  w: "workflows",
  r: "audits",
  s: "settings",
} as const;

/** Shortcuts that work on every page: search, create, go to (G then a letter), help (?). */
export function GlobalShortcuts() {
  const router = useRouter();
  const t = useTranslations("shell");
  const tNav = useTranslations("nav");
  const goPending = useRef(0);
  const canCreate = useCan("workflow:write");
  const [listed, setListed] = useState<ReturnType<typeof shortcuts.list>>([]);

  useShortcut("mod+k", openCommandPalette, { description: t("search") });
  useShortcut("/", openCommandPalette, { description: t("search") });
  // C creates, unless it ends a G sequence (G then C opens the control room).
  useShortcut("c", () => router.push("/workflows/new"), {
    when: () => canCreate && Date.now() - goPending.current >= SEQUENCE_MS,
    description: tNav("newWorkflow"),
  });
  useShortcut(
    "g",
    () => {
      goPending.current = Date.now();
    },
    { description: `G ${t("then")} O, C, W, R, S` }
  );
  const go = (key: keyof typeof GO_KEYS) => ({
    run: () => {
      goPending.current = 0;
      router.push(GO_KEYS[key]);
    },
    options: {
      when: () => Date.now() - goPending.current < SEQUENCE_MS,
      description: t("goTo", { page: tNav(GO_LABELS[key]) }),
    },
  });
  const [o, c, w, r, s] = [go("o"), go("c"), go("w"), go("r"), go("s")];
  useShortcut("o", o.run, o.options);
  useShortcut("c", c.run, c.options);
  useShortcut("w", w.run, w.options);
  useShortcut("r", r.run, r.options);
  useShortcut("s", s.run, s.options);
  useShortcut(
    "shift+?",
    () => {
      setListed(shortcuts.list());
      void help.open();
    },
    { description: t("shortcuts") }
  );

  return (
    <>
      <CommandPalette />
      <Dialog controller={help}>
        <DialogBackdrop />
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>{t("shortcuts")}</DialogTitle>
            <DialogDescription>{t("shortcutsHint")}</DialogDescription>
          </DialogHeader>
          <DialogBody>
            {listed.length ? (
              <ul className="flex flex-col">
                {Array.from(
                  Map.groupBy(listed, (entry) => entry.description ?? ""),
                  ([description, entries]) => (
                    <li
                      key={description}
                      className="flex h-8 items-center justify-between gap-4 border-t border-line text-[13px] first:border-t-0"
                    >
                      <span className="text-ink-2 first-letter:uppercase">{description}</span>
                      <span className="flex gap-1">
                        {entries.map((entry) => (
                          <Kbd key={entry.keys}>{entry.hint}</Kbd>
                        ))}
                      </span>
                    </li>
                  )
                )}
              </ul>
            ) : (
              <p className="text-[13px] text-ink-3">{t("noShortcuts")}</p>
            )}
          </DialogBody>
        </DialogContent>
      </Dialog>
    </>
  );
}
