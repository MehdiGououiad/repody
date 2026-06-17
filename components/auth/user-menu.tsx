"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { LogOut, ShieldCheck, UserRound } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { initialsFromSession, realmRolesFromAccessToken } from "@/lib/auth/jwt-claims";
import { usePlatformAuth } from "@/lib/hooks/use-platform-auth";
import { signOut } from "next-auth/react";
import { cn } from "@/lib/utils";

export function UserMenu() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const { oidcEnabled, loading: authLoading } = usePlatformAuth();

  if (authLoading || status === "loading") {
    return (
      <div
        className="ml-1 hidden size-8 animate-pulse rounded-full bg-muted sm:block"
        aria-hidden
      />
    );
  }

  if (!oidcEnabled) {
    return (
      <div
        className="ml-1 hidden max-w-[10rem] truncate rounded-full border border-border/80 bg-surface-container-low px-2.5 py-1 text-[10px] font-medium text-muted-foreground sm:block"
        title={t("devModeHint")}
      >
        {t("devModeBadge")}
      </div>
    );
  }

  const email = session?.user?.email ?? undefined;
  const name = session?.user?.name ?? undefined;
  const initials = initialsFromSession(name, email);
  const roles = realmRolesFromAccessToken(session?.accessToken);
  const primaryRole = roles[0] ?? t("roleUnknown");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="ml-1 hidden size-9 rounded-full p-0 sm:inline-flex"
          aria-label={t("accountMenu", { name: name ?? email ?? t("account") })}
        >
          <span
            className={cn(
              "flex size-8 items-center justify-center rounded-full bg-gradient-to-br",
              "from-accent-blue/30 to-sidebar-accent text-xs font-semibold ring-1 ring-accent-blue/30"
            )}
          >
            {initials}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium leading-none">{name ?? email ?? t("account")}</p>
            {email ? (
              <p className="text-xs text-muted-foreground truncate">{email}</p>
            ) : null}
            <p className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-muted-foreground">
              <ShieldCheck className="h-3 w-3" aria-hidden />
              {primaryRole}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled className="text-xs text-muted-foreground">
          <UserRound className="mr-2 h-4 w-4" />
          {t("managedInKeycloak")}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={() => void signOut({ callbackUrl: "/login" })}
        >
          <LogOut className="mr-2 h-4 w-4" />
          {t("signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
