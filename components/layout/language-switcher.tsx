"use client";

import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Languages, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { setLocale } from "@/app/actions/set-locale";
import { locales, type Locale } from "@/i18n/config";

const languages: Record<Locale, { label: string; short: string }> = {
  en: { label: "English", short: "EN" },
  fr: { label: "Français", short: "FR" },
};

export function LanguageSwitcher() {
  const current = useLocale() as Locale;
  const t = useTranslations("topbar");
  const [pending, startTransition] = useTransition();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-9 px-2 gap-1.5 font-medium"
          aria-label={t("language")}
          disabled={pending}
        >
          <Languages className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase">
            {languages[current].short}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[160px]">
        {locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() =>
              startTransition(() => {
                setLocale(loc);
              })
            }
            className="justify-between"
          >
            <span>{languages[loc].label}</span>
            {loc === current ? <Check className="h-4 w-4" /> : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
