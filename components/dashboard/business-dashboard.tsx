"use client";

import { AlertTriangle, ArrowUpRight } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { GetStartedPanel } from "@/components/dashboard/get-started-panel";
import { HealthStrip } from "@/components/dashboard/health-strip";
import { QueueLiveBadge } from "@/components/dashboard/queue-live-badge";
import { RecentAuditsTable } from "@/components/dashboard/recent-audits-table";
import { WorkflowSummaryList } from "@/components/dashboard/workflow-summary-list";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { $api } from "@/lib/api/browser";
import type { Audit } from "@/lib/types";

const REFRESH_MS = 30_000;

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
  if (audits.length === 0) return null;
  return (
    <div className="panel-elevated rounded-xl border-danger/25 bg-danger/5 px-5 py-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-danger" />
          <p className="text-sm font-semibold text-danger">{t("openFailures")}</p>
        </div>
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-danger hover:text-danger gap-1"
        >
          <Link href="/audits?outcome=failed">
            {t("viewAll")}
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </Button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {audits.map((audit) => (
          <Link
            key={audit.id}
            href={`/audits/${audit.id}`}
            className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg bg-card border border-danger/20 hover:border-danger/40 transition-colors group"
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-on-surface truncate group-hover:text-danger transition-colors">
                {audit.workflowName}
              </p>
              <p className="text-[11px] text-on-surface-variant truncate">{audit.id}</p>
            </div>
            <Badge variant="danger" className="text-[10px] shrink-0">
              {t("failedRulesBadge", { count: audit.failedRules })}
            </Badge>
          </Link>
        ))}
      </div>
    </div>
  );
}

function LiveIndicator({ updatedAt }: { updatedAt: number }) {
  const t = useTranslations("dashboard.live");
  const format = useFormatter();
  if (!updatedAt) return null;
  return (
    <p className="text-[11px] text-on-surface-variant flex items-center gap-2">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
      </span>
      {t("updated", { time: format.dateTime(updatedAt, { hour: "2-digit", minute: "2-digit" }) })}
    </p>
  );
}

/** The dashboard, prefetched by the page and refreshed every 30 s while it is open. */
export function BusinessDashboard() {
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const { data, dataUpdatedAt } = $api.useSuspenseQuery("get", "/v1/dashboard", undefined, {
    refetchInterval: REFRESH_MS,
    staleTime: REFRESH_MS,
  });

  const auditsThisWeek = data.kpis.find((k) => k.id === "auditsWeek")?.value ?? 0;
  return (
    <div className="space-y-6">
      {data.workflows.length === 0 || auditsThisWeek === 0 ? <GetStartedPanel /> : null}
      <HealthStrip staleRuns={data.staleRuns} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <LiveIndicator updatedAt={dataUpdatedAt} />
        <QueueLiveBadge queue={data.queue} />
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-on-surface">
          {t("auditActivity")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
          {data.kpis.map((metric) => (
            <KpiCard key={metric.id} metric={metric} />
          ))}
        </div>
      </section>

      <AttentionRow audits={data.failedAudits} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <PerformanceChart data={data.performanceSeries} />
        </div>
        <ViolationsBreakdown items={data.failuresBySeverity} />
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-on-surface">
            {t("recentSubmissions")}
          </h2>
          <Link
            href="/audits"
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            {tCommon("viewAll")}
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        <RecentAuditsTable audits={data.recentAudits} />
      </section>

      <WorkflowSummaryList workflows={data.workflows} />
    </div>
  );
}
