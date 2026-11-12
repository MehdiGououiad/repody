"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";

export default function UnauthorizedPage() {
  const t = useTranslations("auth");
  return (
    <main className="flex min-h-dvh items-center justify-center bg-canvas px-4">
      <div className="flex w-full max-w-sm flex-col gap-5 pb-[10vh]">
        <StatusGlyph status="failed" className="size-5" />
        <div className="flex flex-col gap-1.5">
          <h1 className="text-xl font-semibold text-ink">{t("forbiddenTitle")}</h1>
          <p className="text-sm text-ink-3">{t("forbiddenBody")}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href="/dashboard">{t("backToDashboard")}</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link href="/login">{t("switchAccount")}</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
