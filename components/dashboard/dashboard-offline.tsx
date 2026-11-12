import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";

/** Shown instead of the overview when the API cannot be reached. */
export function DashboardOffline() {
  const t = useTranslations("dashboard");
  return (
    <div className="flex flex-col items-start gap-3 py-10">
      <p className="flex items-center gap-2 text-sm font-medium text-ink">
        <StatusGlyph status="failed" />
        {t("offlineTitle")}
      </p>
      <p className="max-w-md text-sm text-ink-3">{t("offlineHint")}</p>
      <Button asChild variant="secondary" size="sm">
        <Link href="/workflows/new">{t("offlineCta")}</Link>
      </Button>
    </div>
  );
}
