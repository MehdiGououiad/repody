import { Plus } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { DashboardOffline } from "@/components/dashboard/dashboard-offline";
import { GetStartedPanel } from "@/components/dashboard/get-started-panel";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { fetchDashboardBundle } from "@/lib/api/dashboard-server";

const BusinessDashboard = dynamic(
  () =>
    import("@/components/dashboard/business-dashboard").then((m) => ({
      default: m.BusinessDashboard,
    })),
  { loading: () => <div className="space-y-4 animate-pulse h-[480px] panel-elevated rounded-xl" /> }
);

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
        <DashboardOffline />
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

      {showGetStarted ? <GetStartedPanel /> : null}

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
