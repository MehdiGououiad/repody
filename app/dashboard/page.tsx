import Link from "next/link";
import dynamic from "next/dynamic";
import { Plus, GitBranch } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { GetStartedPanel } from "@/components/dashboard/get-started-panel";
import { fetchDashboardBundle } from "@/lib/api/dashboard";

const BusinessDashboard = dynamic(
  () =>
    import("@/components/dashboard/business-dashboard").then((m) => ({
      default: m.BusinessDashboard,
    })),
  { loading: () => <div className="space-y-4 animate-pulse h-[480px] panel-elevated rounded-xl" /> }
);

function EmptyDashboard({ t }: { t: Awaited<ReturnType<typeof getTranslations<"dashboard">>> }) {
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

export default async function DashboardPage() {
  const [t, tCommon, data] = await Promise.all([
    getTranslations("dashboard"),
    getTranslations("common"),
    fetchDashboardBundle(),
  ]);

  const auditsWeek = data.kpis.find((k) => k.id === "auditsWeek")?.rawValue ?? 0;
  const showGetStarted = data.workflows.length === 0 || auditsWeek === 0;

  if (!data.apiLive) {
    return (
      <PageShell>
        <PageHeader title={t("title")} description={t("pageDescription")} />
        <EmptyDashboard t={t} />
      </PageShell>
    );
  }

  return (
    <PageShell.Stagger>
      <PageHeader
        title={t("title")}
        description={t("pageDescription")}
        actions={
          <Link href="/workflows/new">
            <Button size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              {tCommon("newWorkflow")}
            </Button>
          </Link>
        }
      />

      <GetStartedPanel show={showGetStarted} />

      <BusinessDashboard
        initial={{
          apiLive: data.apiLive,
          kpis: data.kpis,
          audits: data.audits,
          workflows: data.workflows,
          performanceSeries: data.performanceSeries,
          violationBreakdown: data.violationBreakdown,
          healthAlerts: data.healthAlerts,
          queue: data.queue,
        }}
      />
    </PageShell.Stagger>
  );
}
