import { GitBranch, Plus } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

/** Shown instead of the dashboard when the API is unreachable. */
export function DashboardOffline() {
  const t = useTranslations("dashboard");
  return (
    <div className="panel-elevated rounded-xl border-dashed px-6 py-14 text-center space-y-4">
      <div className="mx-auto size-12 rounded-full bg-accent-blue/10 flex items-center justify-center ring-1 ring-accent-blue/20">
        <GitBranch className="h-5 w-5 text-accent-blue" />
      </div>
      <p className="text-sm font-semibold text-on-surface">{t("offlineTitle")}</p>
      <p className="text-sm text-on-surface-variant max-w-md mx-auto">{t("offlineHint")}</p>
      <Link href="/workflows/new">
        <Button size="sm" className="gap-2 mt-2">
          <Plus className="h-4 w-4" />
          {t("offlineCta")}
        </Button>
      </Link>
    </div>
  );
}
