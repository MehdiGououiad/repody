"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useCallback, useRef } from "react";
import { When } from "@/components/audit/run-row";
import { ListKeysHint, useListKeys } from "@/components/layout/list-keys";
import { AnimatedNumber } from "@/components/shared/animated-number";
import { Figure } from "@/components/shared/figure";
import { Sparkline } from "@/components/shared/sparkline";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { reviewCount } from "@/lib/audits/review";
import { EASE_OUT, rowEnter } from "@/lib/motion";
import type { Dashboard, Kpi } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";
import { Activity, CardHeader, card, DocumentsRead, HourHeatmap } from "./insights";
import { VolumeChart } from "./volume-chart";

const REFRESH_MS = 10_000;

/** What is happening now: the queue, the model, the last refresh. */
function Pulse({ data, updatedAt }: { data: Dashboard; updatedAt: number }) {
  const t = useTranslations("dashboard");
  const platform = $api.useQuery("get", "/v1/platform/config", undefined, {
    refetchInterval: 30_000,
  }).data;
  const { runningRuns, queuedRuns } = data.queue;
  const model =
    platform?.modelAvailable === true
      ? { text: t("pulse.modelAwake"), dot: "bg-pass" }
      : platform?.modelAvailable === false
        ? { text: t("pulse.modelDown"), dot: "bg-fail" }
        : { text: t("pulse.modelAsleep"), dot: "bg-ink-4" };
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-ink-3">
      <span className="flex items-center gap-1.5">
        {runningRuns ? (
          <span className="relative flex size-2">
            <span className="absolute inset-0 animate-ping rounded-full bg-accent opacity-60 motion-reduce:hidden" />
            <span className="relative size-2 rounded-full bg-accent" />
          </span>
        ) : (
          <span className="size-2 rounded-full bg-pass" />
        )}
        <span className={runningRuns ? "font-medium text-accent-ink" : undefined}>
          {t("pulse.running", { count: runningRuns })}
        </span>
        {queuedRuns ? <span>· {t("pulse.queued", { count: queuedRuns })}</span> : null}
      </span>
      {platform ? (
        <span className="flex items-center gap-1.5">
          <span className={cn("size-2 rounded-full", model.dot)} />
          {model.text}
        </span>
      ) : null}
      {updatedAt ? (
        <span className="ms-auto text-ink-4">
          {t("pulse.updated")} <When value={new Date(updatedAt).toISOString()} />
        </span>
      ) : null}
    </div>
  );
}

function Delta({ metric }: { metric: Kpi }) {
  const t = useTranslations("dashboard.kpi");
  const format = useFormatter();
  const change = metric.value - metric.previous;
  if (change === 0) return <span className="text-xs text-ink-4">{t("same")}</span>;
  const good = metric.id === "failures" ? change < 0 : change > 0;
  const delta =
    metric.id === "passRate"
      ? t("deltaPoints", {
          delta: format.number(Math.abs(change) * 100, { maximumFractionDigits: 1 }),
        })
      : format.number(Math.abs(Math.round(change)));
  return (
    <span
      title={t("vsLastWeek")}
      className={cn("text-xs tabular-nums", good ? "text-pass-ink" : "text-fail-ink")}
    >
      {change > 0 ? "↑" : "↓"} {delta}
    </span>
  );
}

function StatStrip({ data }: { data: Dashboard }) {
  const t = useTranslations("dashboard.stats");
  const format = useFormatter();
  const kpi = (id: Kpi["id"]) => data.kpis.find((k) => k.id === id);
  const runs = kpi("auditsWeek");
  const rate = kpi("passRate");
  const week = data.performanceSeries.slice(-7);
  const toReview = reviewCount(data.performanceSeries);
  const sources = data.sources.api + data.sources.test;
  const integer = useCallback((v: number) => format.number(Math.round(v)), [format]);
  const percent = useCallback(
    (v: number) => format.number(v, { style: "percent", maximumFractionDigits: 1 }),
    [format]
  );
  const duration = useCallback((v: number) => formatDurationMs(Math.round(v)), []);

  return (
    <div
      className={cn(
        card,
        "grid grid-cols-2 divide-line md:grid-cols-3 xl:grid-cols-5 [&>*]:border-line max-md:[&>*:nth-child(odd)]:border-e md:[&>*:not(:nth-child(3n))]:border-e xl:[&>*]:border-e xl:[&>*:last-child]:border-e-0 [&>*]:border-b xl:[&>*]:border-b-0"
      )}
    >
      {runs ? (
        <Figure
          label={t("runs")}
          value={<AnimatedNumber value={runs.value} format={integer} />}
          foot={<Delta metric={runs} />}
          chart={<Sparkline values={runs.series.map((p) => p.value)} />}
        />
      ) : null}
      {rate ? (
        <Figure
          label={t("passRate")}
          value={runs?.value ? <AnimatedNumber value={rate.value} format={percent} /> : "—"}
          tone={rate.value < 0.8 && runs?.value ? "text-warn-ink" : undefined}
          foot={
            runs?.value ? (
              <Delta metric={rate} />
            ) : (
              <span className="text-xs text-ink-4">{t("noRunsYet")}</span>
            )
          }
          chart={<Sparkline values={rate.series.map((p) => p.value)} className="text-pass" />}
        />
      ) : null}
      <Figure
        label={t("toReview")}
        value={<AnimatedNumber value={toReview} format={integer} />}
        tone={toReview ? "text-fail-ink" : undefined}
        foot={
          <Link
            href="/audits?outcome=review"
            className="text-xs tabular-nums text-ink-4 hover:text-ink"
          >
            {t("reviewSplit", {
              failed: week.reduce((sum, d) => sum + d.failed, 0),
              warning: week.reduce((sum, d) => sum + d.warning, 0),
            })}
          </Link>
        }
        chart={<Sparkline values={week.map((d) => d.warning + d.failed)} className="text-fail" />}
      />
      <Figure
        label={t("duration")}
        value={
          data.timing.medianMs ? (
            <AnimatedNumber value={data.timing.medianMs} format={duration} />
          ) : (
            "—"
          )
        }
        foot={
          <span className="text-xs tabular-nums text-ink-4">
            {t("p95", { value: formatDurationMs(data.timing.p95Ms) })} ·{" "}
            {t("extraction", { value: formatDurationMs(data.timing.extractionMedianMs) })}
          </span>
        }
      />
      <Figure
        label={t("api")}
        value={<AnimatedNumber value={sources ? data.sources.api / sources : 0} format={percent} />}
        foot={
          <span className="text-xs tabular-nums text-ink-4">
            {t("apiSplit", { api: data.sources.api, test: data.sources.test })}
          </span>
        }
        chart={
          <span className="flex h-1.5 w-16 overflow-hidden rounded-full bg-selected" aria-hidden>
            <motion.span
              className="h-full bg-accent"
              initial={{ width: 0 }}
              animate={{ width: `${sources ? (data.sources.api / sources) * 100 : 0}%` }}
              transition={{ duration: 0.5, ease: EASE_OUT }}
            />
          </span>
        }
      />
    </div>
  );
}

/** The review queue, compact: what failed, on which workflow, when. */
function ReviewQueue({ audits }: { audits: Dashboard["failedAudits"] }) {
  const t = useTranslations("dashboard");
  const tAudits = useTranslations("audits");
  const tCommon = useTranslations("common");
  const ref = useRef<HTMLUListElement>(null);
  useListKeys(ref);
  return (
    <section className={card}>
      <CardHeader
        title={t("queueTitle")}
        hint={t("queueHint")}
        action={
          audits.length ? (
            <Button variant="ghost" size="xs" render={<Link href="/audits?outcome=review" />}>
              {tCommon("viewAll")}
            </Button>
          ) : null
        }
      />
      {audits.length ? (
        <>
          <ul ref={ref} className="flex-1 divide-y divide-line">
            {audits.map((audit, index) => (
              <motion.li key={audit.id} {...rowEnter(index)}>
                <Link
                  href={`/audits/${audit.id}`}
                  data-row
                  className={cn(
                    "grid grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2 outline-none transition-colors duration-100 hover:bg-hover focus-visible:bg-selected",
                    audit.status === "failed" ? "bg-fail-wash/30" : "bg-warn-wash/30"
                  )}
                >
                  <StatusGlyph status={audit.status} label={tAudits(`status.${audit.status}`)} />
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-ink">
                      {audit.workflowName}
                    </span>
                    <span
                      className={cn(
                        "block truncate text-xs",
                        audit.status === "failed" ? "text-fail-ink" : "text-warn-ink"
                      )}
                    >
                      {audit.firstFailedRule ??
                        (audit.uncheckedRule
                          ? tAudits("row.unchecked", { rule: audit.uncheckedRule })
                          : audit.unconfirmedFields
                            ? tAudits("row.unconfirmed", { count: audit.unconfirmedFields })
                            : tAudits("row.noFields"))}
                    </span>
                  </span>
                  <span className="text-xs tabular-nums text-ink-4">
                    <When value={audit.timestamp} />
                  </span>
                </Link>
              </motion.li>
            ))}
          </ul>
          <div className="flex h-8 items-center border-t border-line px-4">
            <ListKeysHint />
          </div>
        </>
      ) : (
        <p className="flex flex-1 items-center gap-2 px-4 py-6 text-[13px] text-ink-3">
          <StatusGlyph status="passed" />
          {t("nothingToReview")}
        </p>
      )}
    </section>
  );
}

/** Each workflow: its documents, its last 7 days, how often it passes, how long it takes. */
function WorkflowTable({ data }: { data: Dashboard }) {
  const t = useTranslations("dashboard.workflowsTable");
  const tDash = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const format = useFormatter();
  const activity = new Map(data.workflowActivity.map((a) => [a.workflowId, a]));
  const grid =
    "grid grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-3 md:grid-cols-[14px_minmax(0,1fr)_80px_64px_160px_64px_120px]";
  return (
    <section className={card}>
      <CardHeader
        title={t("title")}
        action={
          <Button variant="ghost" size="xs" render={<Link href="/workflows" />}>
            {tCommon("viewAll")}
          </Button>
        }
      />
      <div
        className={cn(
          "hidden h-7 border-b border-line bg-raised px-4 text-xs text-ink-4 md:grid",
          grid
        )}
      >
        <span />
        <span />
        <span>{t("activity")}</span>
        <span className="text-end">{t("runs")}</span>
        <span>{t("passRate")}</span>
        <span className="text-end">{t("duration")}</span>
        <span className="text-end">{t("lastRun")}</span>
      </div>
      <ul className="divide-y divide-line">
        {data.workflows.map((workflow, index) => {
          const days = activity.get(workflow.id);
          const week = days?.runs.reduce((a, b) => a + b, 0) ?? 0;
          return (
            <motion.li key={workflow.id} {...rowEnter(index)}>
              <Link
                href={`/workflows/${workflow.id}/edit`}
                className={cn("h-10 px-4 transition-colors duration-100 hover:bg-hover", grid)}
              >
                <StatusGlyph status={workflow.status === "active" ? "live" : "draft"} />
                <span className="truncate text-[13px] font-medium text-ink">{workflow.name}</span>
                <span className="hidden md:block">
                  {days && week ? (
                    <Sparkline values={days.runs} width={72} height={18} />
                  ) : (
                    <span className="text-xs text-ink-4">—</span>
                  )}
                </span>
                <span className="hidden text-end text-xs tabular-nums text-ink-2 md:block">
                  {format.number(week)}
                </span>
                <span className="hidden items-center gap-2 md:flex">
                  {workflow.totalRuns ? (
                    <>
                      <span className="h-1 flex-1 overflow-hidden rounded-full bg-fail-wash">
                        <motion.span
                          className="block h-full rounded-full bg-pass"
                          initial={{ width: 0 }}
                          animate={{ width: `${workflow.successRate * 100}%` }}
                          transition={{ duration: 0.5, ease: EASE_OUT, delay: index * 0.03 }}
                        />
                      </span>
                      <span className="w-9 text-end text-xs tabular-nums text-ink-3">
                        {Math.round(workflow.successRate * 100)}%
                      </span>
                    </>
                  ) : (
                    <span className="text-xs text-ink-4">—</span>
                  )}
                </span>
                <span className="hidden text-end text-xs tabular-nums text-ink-3 md:block">
                  {days?.medianMs ? formatDurationMs(days.medianMs) : "—"}
                </span>
                <span className="truncate whitespace-nowrap text-end text-xs tabular-nums text-ink-3">
                  {workflow.lastRun ? (
                    <When value={workflow.lastRun} />
                  ) : (
                    tDash("workflows.neverRun")
                  )}
                </span>
              </Link>
            </motion.li>
          );
        })}
      </ul>
    </section>
  );
}

function GetStarted() {
  const t = useTranslations("dashboard.getStarted");
  const tSteps = useTranslations("workflows.builder.steps");
  const steps = ["fields", "rules", "testDeploy"] as const;
  return (
    <section className={cn(card, "flex-col gap-4 p-5 md:flex-row md:items-center")}>
      <div className="flex-1">
        <h2 className="text-[13px] font-semibold text-ink">{t("title")}</h2>
        <ol className="mt-3 flex flex-col gap-2 md:flex-row md:gap-6">
          {steps.map((key, i) => (
            <li key={key} className="flex items-center gap-2 text-[13px] text-ink-2">
              <span className="flex size-5 items-center justify-center rounded-full bg-accent-wash text-2xs font-semibold tabular-nums text-accent-ink">
                {i + 1}
              </span>
              {tSteps(key)}
            </li>
          ))}
        </ol>
      </div>
      <Button variant="primary" render={<Link href="/workflows/new" />}>
        {t("cta")}
      </Button>
    </section>
  );
}

/** The overview: what is happening now, what needs a person, how the fortnight went, where it
 * fails, and each workflow. Live every 10 s. */
export function BusinessDashboard() {
  const t = useTranslations("dashboard.volume");
  const { data, dataUpdatedAt } = $api.useSuspenseQuery("get", "/v1/dashboard", undefined, {
    refetchInterval: REFRESH_MS,
    staleTime: REFRESH_MS,
  });
  const empty = data.workflows.length === 0 || data.performanceSeries.every((d) => d.runs === 0);

  return (
    <div className="flex flex-col gap-4">
      <Pulse data={data} updatedAt={dataUpdatedAt} />
      {empty ? <GetStarted /> : null}
      <StatStrip data={data} />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className={card}>
          <CardHeader title={t("title")} hint={t("hint")} />
          <div className="flex-1 p-4">
            <VolumeChart series={data.performanceSeries} />
          </div>
        </section>
        <ReviewQueue audits={data.failedAudits} />
      </div>
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <HourHeatmap hourly={data.hourly} />
        <DocumentsRead stats={data.documents} />
        <Activity audits={data.recentAudits.slice(0, 6)} />
      </div>
      {data.workflows.length ? <WorkflowTable data={data} /> : null}
    </div>
  );
}
