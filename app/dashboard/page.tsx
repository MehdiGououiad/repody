import Link from "next/link";
import dynamic from "next/dynamic";
import {
  Plus,
  FileCheck2,
  CheckCircle2,
  Clock,
  GitBranch,
  ArrowUpRight,
  AlertTriangle,
} from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { ViolationsBreakdown } from "@/components/dashboard/violations-breakdown";
import { RecentAuditsTable } from "@/components/dashboard/recent-audits-table";
import { fetchAudits, fetchMetrics, fetchWorkflows } from "@/lib/api/client";
import type { Audit, Workflow, ViolationBreakdown } from "@/lib/types";
import type { KpiMetric } from "@/lib/types";

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

function WorkflowStatusRow({
  t,
  workflows,
}: {
  t: Awaited<ReturnType<typeof getTranslations<"dashboard">>>;
  workflows: Workflow[];
}) {
  const active = workflows.filter((w) => w.status === "active");
  const draft = workflows.filter((w) => w.status === "draft");
  const paused = workflows.filter((w) => w.status === "paused");

  return (
    <div className="panel-elevated rounded-xl px-5 py-4 flex flex-col sm:flex-row sm:items-center gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <GitBranch className="h-4 w-4 text-primary" />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("workflowStatus")}
          </p>
          <p className="text-lg font-bold text-on-surface leading-tight">
            {workflows.length} {t("workflowsTotal")}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 flex-wrap">
        <span className="flex items-center gap-1.5 text-xs font-medium text-success">
          <CheckCircle2 className="h-3.5 w-3.5" />
          {active.length} {t("workflowActive")}
        </span>
        {paused.length > 0 && (
          <span className="flex items-center gap-1.5 text-xs font-medium text-warning">
            <Clock className="h-3.5 w-3.5" />
            {paused.length} {t("workflowPaused")}
          </span>
        )}
        {draft.length > 0 && (
          <span className="flex items-center gap-1.5 text-xs font-medium text-on-surface-variant">
            <FileCheck2 className="h-3.5 w-3.5" />
            {draft.length} {t("workflowDraft")}
          </span>
        )}
      </div>
      <Link href="/workflows" className="sm:ml-auto shrink-0">
        <Button variant="outline" size="sm" className="gap-1.5 h-8 text-xs">
          {t("manageWorkflows")}
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Button>
      </Link>
    </div>
  );
}

function FailedAuditRow({
  t,
  audits,
}: {
  t: Awaited<ReturnType<typeof getTranslations<"dashboard">>>;
  audits: Audit[];
}) {
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
        {failed.map((a) => (
          <Link
            key={a.id}
            href={`/audits/${a.id}`}
            className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-card border border-danger/20 hover:border-danger/40 transition-colors group"
          >
            <div className="min-w-0">
              <p className="text-xs font-mono font-semibold text-on-surface truncate group-hover:text-danger transition-colors">
                {a.id}
              </p>
              <p className="text-[11px] text-on-surface-variant truncate">{a.entity}</p>
            </div>
            <Badge variant="danger" className="text-[10px] shrink-0">
              {a.failedRules} {t("failedRulesBadge")}
            </Badge>
          </Link>
        ))}
      </div>
    </div>
  );
}

function EmptyDashboard({ t }: { t: Awaited<ReturnType<typeof getTranslations<"dashboard">>> }) {
  return (
    <div className="panel-elevated rounded-xl border-dashed px-6 py-14 text-center space-y-4">
      <div className="mx-auto size-12 rounded-full bg-accent-blue/10 flex items-center justify-center ring-1 ring-accent-blue/20">
        <GitBranch className="h-5 w-5 text-accent-blue" />
      </div>
      <p className="text-sm font-semibold text-on-surface">{t("title")}</p>
      <p className="text-sm text-on-surface-variant max-w-md mx-auto">
        Connect the API to load live metrics. Start the stack with{" "}
        <code className="font-mono text-xs">docker compose up api</code>.
      </p>
      <Link href="/workflows/new">
        <Button size="sm" className="gap-2 mt-2">
          <Plus className="h-4 w-4" />
          Create workflow
        </Button>
      </Link>
    </div>
  );
}

export default async function DashboardPage() {
  const [t, tCommon] = await Promise.all([
    getTranslations("dashboard"),
    getTranslations("common"),
  ]);

  let kpis: KpiMetric[] = [];
  let performanceSeries: { day: string; runs: number; prevRuns: number }[] = [];
  let violationBreakdown: ViolationBreakdown[] = [];
  let audits: Audit[] = [];
  let workflows: Workflow[] = [];
  let apiLive = false;

  try {
    const [metrics, auditRes, wfList] = await Promise.all([
      fetchMetrics(),
      fetchAudits(),
      fetchWorkflows(),
    ]);
    kpis = metrics.kpis;
    performanceSeries = metrics.performanceSeries;
    violationBreakdown = metrics.violationBreakdown;
    audits = auditRes.audits;
    workflows = wfList;
    apiLive = true;
  } catch {
    apiLive = false;
  }

  if (!apiLive) {
    return (
      <PageShell>
        <PageHeader
          title={t("title")}
          description={t("pageDescription")}
          eyebrow="Overview"
        />
        <EmptyDashboard t={t} />
      </PageShell>
    );
  }

  return (
    <PageShell.Stagger>
      <PageHeader
        title={t("title")}
        description={t("pageDescription")}
        eyebrow="Overview"
        actions={
          <Link href="/workflows/new">
            <Button size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              {tCommon("newWorkflow")}
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {kpis.slice(0, 4).map((m) => (
          <KpiCard key={m.id} metric={m} />
        ))}
      </div>

      <FailedAuditRow t={t} audits={audits} />
      <WorkflowStatusRow t={t} workflows={workflows} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <PerformanceChart data={performanceSeries} />
        </div>
        <ViolationsBreakdown items={violationBreakdown} />
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-on-surface">{t("recentSubmissions")}</h2>
          <Link href="/audits" className="text-xs text-primary hover:underline flex items-center gap-1">
            {tCommon("viewAll")}
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        <RecentAuditsTable audits={audits} limit={8} />
      </section>
    </PageShell.Stagger>
  );
}
