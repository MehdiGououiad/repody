import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ArrowUpRight, FlaskConical, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { BenchmarkReport, OperatorJob } from "@/lib/api/operator";

function jobTone(status: OperatorJob["status"]) {
  if (status === "completed") return "success" as const;
  if (status === "failed") return "danger" as const;
  if (status === "running" || status === "queued") return "outline" as const;
  return "outline" as const;
}

export async function OperatorSnapshot({
  jobs,
  benchmark,
}: {
  jobs: OperatorJob[];
  benchmark: BenchmarkReport | null;
}) {
  const t = await getTranslations("dashboard.operator");
  const recent = jobs.slice(0, 5);

  if (!recent.length && !benchmark) return null;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-on-surface">{t("title")}</h2>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
        </div>
        <Link href="/settings?tab=benchmarks">
          <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
            {t("openBenchmarks")}
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {benchmark ? (
          <div className="panel-elevated rounded-xl p-5 xl:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <FlaskConical className="h-4 w-4 text-primary" />
              <p className="text-sm font-semibold text-on-surface">{t("latestBenchmark")}</p>
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-on-surface-variant">
                  {t("passed")}
                </dt>
                <dd className="font-semibold text-success mt-0.5">{benchmark.summary.passed}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-on-surface-variant">
                  {t("failed")}
                </dt>
                <dd className="font-semibold text-danger mt-0.5">{benchmark.summary.failed}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-on-surface-variant">
                  {t("fieldAccuracy")}
                </dt>
                <dd className="font-semibold mt-0.5">
                  {Math.round(benchmark.summary.fieldAccuracy * 100)}%
                </dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-on-surface-variant">
                  {t("profile")}
                </dt>
                <dd className="font-mono text-xs mt-0.5">{benchmark.profile}</dd>
              </div>
            </dl>
          </div>
        ) : null}

        <div
          className={`panel-elevated rounded-xl overflow-hidden ${benchmark ? "xl:col-span-2" : "xl:col-span-3"}`}
        >
          <div className="px-5 py-3 border-b border-border flex items-center gap-2">
            <Wrench className="h-4 w-4 text-on-surface-variant" />
            <p className="text-sm font-semibold text-on-surface">{t("recentJobs")}</p>
          </div>
          {recent.length === 0 ? (
            <p className="px-5 py-6 text-sm text-on-surface-variant">{t("noJobs")}</p>
          ) : (
            <ul className="divide-y divide-border">
              {recent.map((job) => (
                <li
                  key={job.id}
                  className="px-5 py-3 flex flex-wrap items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-on-surface truncate">{job.label}</p>
                    <p className="text-[11px] text-on-surface-variant font-mono truncate">
                      {job.kind} · {job.id}
                    </p>
                  </div>
                  <Badge variant={jobTone(job.status)} className="shrink-0 text-[10px]">
                    {job.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
