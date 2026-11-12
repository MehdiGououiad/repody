"use client";

import * as Sentry from "@sentry/nextjs";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("error");
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="rounded-xl px-6 py-10 text-center space-y-4 max-w-lg mx-auto">
      <h2 className="text-base font-semibold text-ink">{t("title")}</h2>
      <p className="text-sm text-ink-3">{t("section")}</p>
      <div className="flex items-center justify-center gap-2">
        <Button type="button" size="sm" onClick={() => reset()}>
          {t("retry")}
        </Button>
        <Button type="button" size="sm" variant="outline" asChild>
          <Link href="/dashboard">{t("dashboard")}</Link>
        </Button>
      </div>
    </div>
  );
}
