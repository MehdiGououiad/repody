"use client";

import { Check, ChevronsUpDown, LogOut, Monitor, Moon, Sun } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { Suspense, useTransition } from "react";
import { setLocale } from "@/app/actions/preferences";
import { useAccount } from "@/components/auth/account-context";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { type Locale, locales } from "@/i18n/config";
import { initials } from "@/lib/auth/account";
import { signOutToLogin } from "@/lib/auth/client";

const LANGUAGES: Record<Locale, string> = { en: "English", fr: "Français" };
const THEMES = [
  { value: "light", icon: Sun },
  { value: "dark", icon: Moon },
  { value: "system", icon: Monitor },
] as const;

/** The signed-in person, and their preferences: theme, language, sign out. */
export function UserMenu() {
  return (
    <Suspense fallback={<div className="h-8 rounded-md bg-hover" aria-hidden />}>
      <AccountMenu />
    </Suspense>
  );
}

function AccountMenu() {
  const t = useTranslations("auth");
  const tBar = useTranslations("topbar");
  const account = useAccount();
  const { theme, setTheme } = useTheme();
  const locale = useLocale() as Locale;
  const [pending, startTransition] = useTransition();
  const name = account ? (account.name ?? account.email ?? t("account")) : t("devModeBadge");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex h-8 w-full cursor-pointer items-center gap-2 rounded-md px-1.5 text-start transition-colors duration-100 hover:bg-hover data-[state=open]:bg-hover">
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-selected text-2xs font-semibold text-ink-2">
          {account ? initials(account) : "D"}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink-2">{name}</span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-ink-4" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="top"
        align="start"
        className="w-[var(--radix-dropdown-menu-trigger-width)] min-w-56"
      >
        <DropdownMenuLabel>
          <p className="truncate text-sm font-medium text-ink">{name}</p>
          <p className="truncate text-xs font-normal text-ink-3">
            {account ? (account.email ?? account.roles[0]) : t("devModeHint")}
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <fieldset
          className="m-0 flex min-w-0 gap-0.5 border-0 p-1"
          aria-label={tBar("toggleTheme")}
        >
          {THEMES.map(({ value, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => setTheme(value)}
              aria-pressed={theme === value}
              aria-label={tBar(`theme.${value}`)}
              title={tBar(`theme.${value}`)}
              className="flex h-7 flex-1 cursor-pointer items-center justify-center rounded-sm text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink aria-pressed:bg-selected aria-pressed:text-ink"
            >
              <Icon className="size-3.5" aria-hidden />
            </button>
          ))}
        </fieldset>
        <DropdownMenuSeparator />
        {locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            disabled={pending}
            onSelect={() => startTransition(() => setLocale(loc))}
          >
            <span className="flex-1">{LANGUAGES[loc]}</span>
            {loc === locale ? <Check className="size-3.5 text-ink-3" aria-hidden /> : null}
          </DropdownMenuItem>
        ))}
        {account ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void signOutToLogin()}>
              <LogOut aria-hidden />
              {t("signOut")}
            </DropdownMenuItem>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
