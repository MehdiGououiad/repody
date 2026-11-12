"use client";

import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { RunRows, When } from "@/components/audit/run-row";
import { VolumeChart } from "@/components/dashboard/volume-chart";
import { Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import type { Dashboard, Kpi } from "@/lib/types";
import { cn } from "@/lib/utils";

const REFRESH_MS = 30_000;
const frame = "overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]";

/** Where fewer is better, a drop is good news. */
const LOWER_IS_BETTER = new Set<Kpi["id"]>(["failures"]);

function Stat({ metric }: { metric: Kpi }) {
  const t = useTranslations("dashboard.kpi");
  const format = useFormatter();
  const percent = metric.id === "passRate";
  const show = (v: number) =>
    percent
      ? format.number(v, { style: "percent", maximumFractionDigits: 1 })
      : format.number(Math.round(v));
  const change = metric.value - metric.previous;
  const good = LOWER_IS_BETTER.has(metric.id) ? change <= 0 : change >= 0;
  const delta = percent
    ? t("deltaPoints", {
        delta: format.number(Math.abs(change) * 100, { maximumFractionDigits: 1 }),
      })
    : format.number(Math.abs(Math.round(change)));
  return (
    <div className="flex flex-col gap-1 px-5 py-4 first:ps-0 max-sm:px-0">
      <span className="text-xs text-ink-3">{t(metric.id)}</span>
      <span className="text-2xl font-semibold tabular-nums text-ink">{show(metric.value)}</span>
      <span className="text-xs tabular-nums text-ink-3">
        {change === 0 ? (
          t("same")
        ) : (
          <>
            <span className={good ? "text-pass-ink" : "text-fail-ink"}>
              {change > 0 ? "+" : "−"}
              {delta}
            </span>{" "}
            {t("vsLastWeek")}
          </>
        )}
      </span>
    </div>
  );
}

function GetStarted() {
  const t = useTranslations("dashboard.getStarted");
  const tSteps = useTranslations("workflows.builder.steps");
  const steps = ["extract", "rules", "upload"] as const;
  return (
    <section className={cn(frame, "flex flex-col gap-4 p-5 md:flex-row md:items-center")}>
      <div className="flex-1">
        <h2 className="text-sm font-semibold text-ink">{t("title")}</h2>
        <ol className="mt-3 flex flex-col gap-2 md:flex-row md:gap-6">
          {steps.map((key, i) => (
            <li key={key} className="flex items-center gap-2 text-sm text-ink-2">
              <span className="flex size-5 items-center justify-center rounded-full bg-selected text-2xs font-semibold tabular-nums text-ink-2">
                {i + 1}
              </span>
              {tSteps(key)}
            </li>
          ))}
        </ol>
      </div>
      <Button asChild>
        <Link href="/workflows/new">{t("cta")}</Link>
      </Button>
    </section>
  );
}

function Pulse({ data, updatedAt }: { data: Dashboard; updatedAt: number }) {
  const t = useTranslations("dashboard");
  const { runningRuns, queuedRuns } = data.queue;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
      <span className="flex items-center gap-1.5">
        <StatusGlyph status={runningRuns ? "running" : "live"} />
        {runningRuns || queuedRuns
          ? t("queueLive.counts", { running: runningRuns, queued: queuedRuns })
          : t("queueLive.idle")}
      </span>
      {updatedAt ? (
        <span>
          {t("live.updatedPrefix")} <When value={new Date(updatedAt).toISOString()} />
        </span>
      ) : null}
      {data.staleRuns ? (
        <Link href="/audits" className="flex items-center gap-1.5 text-warn-ink hover:underline">
          <StatusGlyph status="warning" />
          {t("stale", { count: data.staleRuns })}
        </Link>
      ) : null}
    </div>
  );
}

/** The overview, prefetched by the page and refreshed every 30 s while it is open. */
export function BusinessDashboard() {
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const { data, dataUpdatedAt } = $api.useSuspenseQuery("get", "/v1/dashboard", undefined, {
    refetchInterval: REFRESH_MS,
    staleTime: REFRESH_MS,
  });
  const runsThisWeek = data.kpis.find((k) => k.id === "auditsWeek")?.value ?? 0;

  return (
    <div className="flex flex-col gap-10">
      <Pulse data={data} updatedAt={dataUpdatedAt} />

      {data.workflows.length === 0 || runsThisWeek === 0 ? <GetStarted /> : null}

      <Section
        title={t("openFailures")}
        hint={data.failedAudits.length ? t("needsReviewHint") : undefined}
        actions={
          data.failedAudits.length ? (
            <Button asChild variant="ghost" size="sm">
              <Link href="/audits?outcome=failed">{tCommon("viewAll")}</Link>
            </Button>
          ) : null
        }
      >
        {data.failedAudits.length ? (
          <div className={frame}>
            <RunRows audits={data.failedAudits} />
          </div>
        ) : (
          <p className="flex items-center gap-2 text-sm text-ink-3">
            <StatusGlyph status="passed" />
            {t("nothingToReview")}
          </p>
        )}
      </Section>

      <section className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 divide-line sm:grid-cols-3 sm:divide-x">
            {data.kpis.map((metric) => (
              <Stat key={metric.id} metric={metric} />
            ))}
          </div>
          <VolumeChart data={data.performanceSeries} />
        </div>
        <Section title={t("violations.title")} hint={t("violations.hint")}>
          {data.failuresBySeverity.length ? (
            <ul className="flex flex-col gap-3">
              {data.failuresBySeverity.map((item) => (
                <li key={item.severity} className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-sm">
                    <span className="text-ink-2">{t(`violations.${item.severity}`)}</span>
                    <span className="tabular-nums text-ink-3">{Math.round(item.share * 100)}%</span>
                  </div>
                  <span className="h-1 overflow-hidden rounded-full bg-selected">
                    <span
                      className={cn(
                        "block h-full rounded-full",
                        item.severity === "reject" ? "bg-fail" : "bg-warn"
                      )}
                      style={{ width: `${item.share * 100}%` }}
                    />
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-3">{t("violations.none")}</p>
          )}
        </Section>
      </section>

      <Section
        title={t("recentSubmissions")}
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link href="/audits">{tCommon("viewAll")}</Link>
          </Button>
        }
      >
        {data.recentAudits.length ? (
          <div className={frame}>
            <RunRows audits={data.recentAudits} />
          </div>
        ) : (
          <p className="text-sm text-ink-3">{t("noRuns")}</p>
        )}
      </Section>
    </div>
  );
}
