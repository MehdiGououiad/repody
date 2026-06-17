"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function UnauthorizedPage() {
  const t = useTranslations("auth");

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive ring-1 ring-destructive/20">
        <ShieldOff className="h-8 w-8" aria-hidden />
      </div>
      <div className="max-w-md space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{t("forbiddenTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("forbiddenBody")}</p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button asChild variant="default">
          <Link href="/dashboard">{t("backToDashboard")}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/login">{t("switchAccount")}</Link>
        </Button>
      </div>
    </div>
  );
}
