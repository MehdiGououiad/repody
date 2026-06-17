"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { AlertTriangle, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { QueueLiveBadge } from "@/components/dashboard/queue-live-badge";
import { RecentAuditsTable } from "@/components/dashboard/recent-audits-table";
import { WorkflowSummaryList } from "@/components/dashboard/workflow-summary-list";
import { useDashboardLive, type LiveDashboardData } from "@/lib/hooks/use-dashboard-live";
import type { Audit } from "@/lib/types";

const KpiCard = dynamic(
  () => import("@/components/dashboard/kpi-card").then((m) => ({ default: m.KpiCard })),
  { loading: () => <div className="panel-elevated rounded-xl h-[120px] animate-pulse" /> }
);

const PerformanceChart = dynamic(
  () =>
    import("@/components/dashboard/performance-chart").then((m) => ({
      default: m.PerformanceChart,
    })),
  { loading: () => <div className="panel-elevated rounded-xl h-[360px] animate-pulse" /> }
);

const ViolationsBreakdown = dynamic(
  () =>
    import("@/components/dashboard/violations-breakdown").then((m) => ({
      default: m.ViolationsBreakdown,
    })),
  { loading: () => <div className="panel-elevated rounded-xl h-[280px] animate-pulse" /> }
);

function AttentionRow({ audits }: { audits: Audit[] }) {
  const t = useTranslations("dashboard");
  const failed = audits.filter((a) => a.status === "failed").slice(0, 3);
  if (failed.length === 0) return null;

  return (
    <div className="panel-elevated rounded-xl border-danger/25 bg-danger/5 px-5 py-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-danger" />
          <p className="text-sm font-semibold text-danger">{t("openFailures")}</p>
        </div>
        <Link href="/audits?status=failed">
          <Button variant="ghost" size="sm" className="h-7 text-xs text-danger hover:text-danger gap-1">
            {t("viewAll")}
            <ArrowUpRight className="h-3 w-3" />
          </Button>
        </Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {failed.map((audit) => (
          <Link
            key={audit.id}
            href={`/audits/${audit.id}`}
            className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg bg-card border border-danger/20 hover:border-danger/40 transition-colors group"
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-on-surface truncate group-hover:text-danger transition-colors">
                {audit.workflowName || audit.entity}
              </p>
              <p className="text-[11px] text-on-surface-variant truncate">{audit.entity}</p>
            </div>
            <Badge variant="danger" className="text-[10px] shrink-0">
              {audit.failedRules} {t("failedRulesBadge")}
            </Badge>
          </Link>
        ))}
      </div>
    </div>
  );
}

function LiveIndicator({ updated }: { updated: Date | null }) {
  const t = useTranslations("dashboard.live");
  if (!updated) return null;

  const time = updated.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <p className="text-[11px] text-on-surface-variant flex items-center gap-2">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
      </span>
      {t("updated", { time })}
    </p>
  );
}

export function BusinessDashboard({
  initial,
}: {
  initial: Omit<LiveDashboardData, "lastUpdated">;
}) {
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const live = useDashboardLive(initial);

  if (!live.apiLive) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <LiveIndicator updated={live.lastUpdated} />
        <QueueLiveBadge />
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-on-surface">{t("auditActivity")}</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          {live.kpis.slice(0, 4).map((metric) => (
            <KpiCard key={metric.id} metric={metric} />
          ))}
        </div>
      </section>

      <AttentionRow audits={live.audits} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <PerformanceChart data={live.performanceSeries} />
        </div>
        <ViolationsBreakdown items={live.violationBreakdown} />
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-on-surface">{t("recentSubmissions")}</h2>
          <Link href="/audits" className="text-xs text-primary hover:underline flex items-center gap-1">
            {tCommon("viewAll")}
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        <RecentAuditsTable audits={live.audits} limit={8} />
      </section>

      <WorkflowSummaryList workflows={live.workflows} />
    </div>
  );
}
