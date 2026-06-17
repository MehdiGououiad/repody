"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { ArrowUpRight, GitBranch } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Workflow } from "@/lib/types";

function passRateLabel(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export function WorkflowSummaryList({ workflows }: { workflows: Workflow[] }) {
  const t = useTranslations("dashboard.workflows");
  const tStatus = useTranslations("workflows.status");

  if (!workflows.length) return null;

  const sorted = [...workflows].sort((a, b) => {
    const rank = (w: Workflow) => (w.status === "active" ? 0 : w.status === "paused" ? 1 : 2);
    return rank(a) - rank(b) || a.name.localeCompare(b.name);
  });

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-display text-base font-semibold text-on-surface">{t("title")}</h2>
        <Link href="/workflows" className="text-xs text-primary hover:underline flex items-center gap-1">
          {t("viewAll")}
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="panel-elevated rounded-xl divide-y divide-border overflow-hidden">
        {sorted.slice(0, 6).map((workflow) => (
          <Link
            key={workflow.id}
            href={`/workflows/${workflow.id}/edit`}
            className="flex items-center gap-4 px-5 py-4 hover:bg-surface-container-lowest/80 transition-colors group"
          >
            <div className="size-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <GitBranch className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-on-surface truncate group-hover:text-primary transition-colors">
                {workflow.name || t("unnamed")}
              </p>
              <p className="text-xs text-on-surface-variant mt-0.5">
                {workflow.totalRuns > 0
                  ? t("runsSummary", {
                      count: workflow.totalRuns,
                      rate: passRateLabel(workflow.successRate),
                    })
                  : t("neverRun")}
              </p>
            </div>
            <Badge
              variant={workflow.status === "active" ? "success" : "outline"}
              className={cn("shrink-0 text-[10px]", workflow.status === "paused" && "border-warning/40 text-warning")}
            >
              {tStatus(workflow.status)}
            </Badge>
          </Link>
        ))}
      </div>
    </section>
  );
}
