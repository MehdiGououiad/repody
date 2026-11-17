"use client";

import { ChevronsUpDown, LogOut, Monitor, Moon, Sun } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { Suspense, use, useTransition } from "react";
import { setLocale } from "@/app/actions/preferences";
import { AccessProvider } from "@/components/auth/access-context";
import { useAccount } from "@/components/auth/account-context";
import {
  Menu,
  MenuContent,
  MenuGroup,
  MenuGroupLabel,
  MenuItem,
  MenuRadio,
  MenuRadioGroup,
  MenuSeparator,
  MenuTrigger,
} from "@/components/ui/menu";
import { SegmentedControl, SegmentedControlOption } from "@/components/ui/segmented-control";
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
  const { roles } = use(AccessProvider);
  const { theme, setTheme } = useTheme();
  const locale = useLocale() as Locale;
  const [pending, startTransition] = useTransition();
  const name = account ? (account.name ?? account.email ?? t("account")) : t("devModeBadge");

  return (
    <Menu onAction={(value) => (value === "sign-out" ? void signOutToLogin() : undefined)}>
      <MenuTrigger className="flex h-8 w-full cursor-pointer items-center gap-2 rounded-md px-1.5 text-start transition-colors duration-100 hover:bg-hover data-open:bg-hover">
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-accent-wash text-2xs font-semibold text-accent-ink">
          {account ? initials(account) : "D"}
        </span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-ink-2">{name}</span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-ink-4" aria-hidden />
      </MenuTrigger>
      <MenuContent side="top" align="start" className="w-(--anchor-width) min-w-60">
        <div className="px-2 pt-1.5 pb-2">
          <p className="truncate text-[13px] font-medium text-ink">{name}</p>
          <p className="truncate text-xs text-ink-3">
            {account ? (account.email ?? roles[0]) : t("devModeHint")}
          </p>
          <SegmentedControl
            aria-label={tBar("toggleTheme")}
            value={theme ?? "system"}
            onValueChange={(value) => value && setTheme(value)}
            className="mt-2.5 flex w-full"
          >
            {THEMES.map(({ value, icon: Icon }) => (
              <SegmentedControlOption
                key={value}
                value={value}
                aria-label={tBar(`theme.${value}`)}
                className="flex-1 justify-center"
              >
                <Icon aria-hidden />
              </SegmentedControlOption>
            ))}
          </SegmentedControl>
        </div>
        <MenuSeparator />
        <MenuGroup>
          <MenuGroupLabel>{tBar("language")}</MenuGroupLabel>
          <MenuRadioGroup
            value={locale}
            onValueChange={(loc) => startTransition(() => setLocale(loc as Locale))}
          >
            {locales.map((loc) => (
              <MenuRadio key={loc} value={loc} disabled={pending}>
                {LANGUAGES[loc]}
              </MenuRadio>
            ))}
          </MenuRadioGroup>
        </MenuGroup>
        {account ? (
          <>
            <MenuSeparator />
            <MenuItem value="sign-out">
              <LogOut aria-hidden />
              {t("signOut")}
            </MenuItem>
          </>
        ) : null}
      </MenuContent>
    </Menu>
  );
}
