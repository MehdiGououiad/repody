"use client";

import * as Sentry from "@sentry/nextjs";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";

/** A page that failed to load: what happened, and the two ways on. */
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
    <div className="mx-auto flex max-w-md flex-col gap-4 px-6 py-20">
      <StatusGlyph status="failed" className="size-5" />
      <div>
        <h2 className="text-base font-semibold text-ink">{t("title")}</h2>
        <p className="mt-1 text-sm text-ink-3">{t("section")}</p>
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={() => reset()}>
          {t("retry")}
        </Button>
        <Button size="sm" variant="ghost" render={<Link href="/dashboard" />}>
          {t("dashboard")}
        </Button>
      </div>
    </div>
  );
}
