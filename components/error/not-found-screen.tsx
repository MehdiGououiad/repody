import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";

/** A link that leads nowhere: say so, and offer the way back. */
export async function NotFoundScreen() {
  const t = await getTranslations("error");
  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 px-6 py-20">
      <StatusGlyph status="skipped" className="size-5" />
      <div>
        <h1 className="text-base font-semibold text-ink">{t("notFoundTitle")}</h1>
        <p className="mt-1 text-sm text-ink-3">{t("notFoundHint")}</p>
      </div>
      <div className="flex gap-2">
        <Button size="sm" render={<Link href="/dashboard" />}>
          {t("dashboard")}
        </Button>
        <Button size="sm" variant="ghost" render={<Link href="/audits" />}>
          {t("runs")}
        </Button>
      </div>
    </div>
  );
}
