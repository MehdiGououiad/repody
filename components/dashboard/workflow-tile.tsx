"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Copy, Check, Play, Pencil, FileSearch, AlertTriangle, XCircle, Clock, Zap } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip } from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Workflow } from "@/lib/types";
import { useHydrated } from "@/lib/hooks/use-hydrated";

function useCopy() {
  const [copied, setCopied] = useState(false);
  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };
  return { copied, copy };
}

function StatusDot({ status }: { status: Workflow["status"] }) {
  return (
    <span className={cn(
      "size-2 rounded-full shrink-0",
      status === "active" ? "bg-success" : status === "paused" ? "bg-warning" : "bg-outline-variant"
    )} />
  );
}

function SuccessBar({ rate, label }: { rate: number; label: string }) {
  const pct = Math.round(rate * 100);
  const color = pct >= 95 ? "bg-success" : pct >= 80 ? "bg-warning" : "bg-danger";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-on-surface-variant">{label}</span>
        <span className={cn("font-semibold", pct >= 95 ? "text-success" : pct >= 80 ? "text-warning" : "text-danger")}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-surface-container-highest overflow-hidden">
        <div className={cn("h-full rounded-full transition-[width]", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function DeployedTile({ workflow }: { workflow: Workflow }) {
  const t = useTranslations("workflows.tile");
  const tCommon = useTranslations("common");
  const tStatus = useTranslations("workflows.status");
  const tNav = useTranslations("nav");
  const { copied, copy } = useCopy();
  const mounted = useHydrated();

  const endpoint = mounted
    ? `${window.location.origin}/api/v1/workflows/${workflow.id}/runs`
    : `/api/v1/workflows/${workflow.id}/runs`;
  const stats = workflow.apiStats!;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden flex flex-col hover:border-outline-variant transition-colors">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <StatusDot status={workflow.status} />
            <h3 className="text-sm font-semibold text-on-surface truncate">{workflow.name}</h3>
          </div>
          <Badge variant={workflow.status === "active" ? "success" : "outline"} className="shrink-0 text-[10px]">
            {tStatus(workflow.status)}
          </Badge>
        </div>
        <p className="text-[11px] text-on-surface-variant mt-1 line-clamp-1 pl-4">{workflow.description}</p>
      </div>

      {/* Endpoint */}
      <div className="px-5 py-3 border-b border-border bg-surface-container-lowest">
        <div className="flex items-center gap-2">
          <Zap className="h-3 w-3 text-primary shrink-0" />
          <code className="text-[10px] font-mono text-on-surface-variant flex-1 truncate">{endpoint}</code>
          <button
            type="button"
            onClick={() => copy(endpoint)}
            aria-label={copied ? tCommon("copied") : tCommon("copy")}
            className={cn(
              "inline-flex items-center justify-center gap-1 min-h-11 min-w-11 px-2 text-[10px] font-mono shrink-0 rounded-md transition-[color,background-color] duration-200 active:scale-[0.98]",
              copied ? "text-success" : "text-on-surface-variant hover:text-on-surface hover:bg-muted/50"
            )}
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            {copied ? tCommon("copied") : tCommon("copy")}
          </button>
        </div>
      </div>

      {/* Stats + sparkline */}
      <div className="px-5 py-4 border-b border-border grid grid-cols-3 gap-4">
        <div>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-wide font-semibold">{t("callsToday")}</p>
          <p className="text-lg font-bold text-on-surface mt-0.5">{stats.apiCallsToday}</p>
        </div>
        <div>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-wide font-semibold">{t("avgLatency")}</p>
          <p className="text-lg font-bold text-on-surface mt-0.5">{stats.avgLatencyMs}ms</p>
        </div>
        <div className="flex items-end">
          {mounted && (
            <ResponsiveContainer width="100%" height={36}>
              <BarChart data={stats.callSeries} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={5}>
                <Bar dataKey="calls" fill="var(--color-primary)" opacity={0.7} radius={[2, 2, 0, 0]} />
                <Tooltip
                  contentStyle={{ fontSize: 10, background: "var(--color-surface-container-high)", border: "none", borderRadius: 6 }}
                  itemStyle={{ color: "var(--color-on-surface)" }}
                  labelStyle={{ color: "var(--color-on-surface-variant)" }}
                  cursor={{ fill: "var(--color-surface-container-highest)" }}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Success rate */}
      <div className="px-5 py-3 border-b border-border">
        <SuccessBar rate={workflow.successRate} label={t("avgSuccessRate")} />
      </div>

      {/* Top failing rules */}
      {stats.topFailingRules.length > 0 && (
        <div className="px-5 py-3 border-b border-border space-y-1.5">
          <p className="text-[10px] text-on-surface-variant uppercase tracking-wide font-semibold mb-2">{t("topFailures")}</p>
          {stats.topFailingRules.slice(0, 2).map((r) => (
            <div key={r.name} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 min-w-0">
                {r.severity === "reject" ? (
                  <XCircle className="h-3 w-3 text-danger shrink-0" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-warning shrink-0" />
                )}
                <span className="text-[11px] text-on-surface truncate">{r.name}</span>
              </div>
              <span className="text-[11px] font-mono text-on-surface-variant shrink-0">{r.count}×</span>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="px-5 py-3 flex items-center gap-2 mt-auto">
        <Link href={`/workflows/${workflow.id}/edit`} className="flex-1">
          <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs">
            <Pencil className="h-3.5 w-3.5" />
            {tCommon("edit")}
          </Button>
        </Link>
        <Link href="/audits" className="flex-1">
          <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs">
            <FileSearch className="h-3.5 w-3.5" />
            {tNav("audits")}
          </Button>
        </Link>
        <Link href={`/workflows/${workflow.id}/edit`}>
          <Button size="sm" className="gap-1.5 text-xs">
            <Play className="h-3.5 w-3.5" />
            {tCommon("test")}
          </Button>
        </Link>
      </div>
    </div>
  );
}

function InactiveTile({ workflow }: { workflow: Workflow }) {
  const t = useTranslations("workflows.tile");
  const tCommon = useTranslations("common");
  const tStatus = useTranslations("workflows.status");

  const fieldCount = workflow.documents.reduce((n, d) => n + d.schema.filter((f) => f.name.trim()).length, 0);

  return (
    <div className="rounded-xl border border-border border-dashed bg-card/60 overflow-hidden flex flex-col hover:bg-card transition-colors">
      <div className="px-5 py-4 flex-1">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <StatusDot status={workflow.status} />
            <h3 className="text-sm font-semibold text-on-surface truncate">{workflow.name}</h3>
          </div>
          <Badge variant="outline" className="shrink-0 text-[10px]">{tStatus(workflow.status)}</Badge>
        </div>
        <p className="text-[11px] text-on-surface-variant line-clamp-2 pl-4">{workflow.description}</p>

        <div className="mt-4 pl-4 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-on-surface-variant">
            <Clock className="h-3 w-3" />
            {workflow.lastRun ? t("lastRun", { date: workflow.lastRun }) : t("neverRun")}
          </div>
          <div className="text-[11px] text-on-surface-variant">
            {workflow.documents.length !== 1 ? t("docTypesPlural", { count: workflow.documents.length }) : t("docTypes", { count: 1 })}
            {fieldCount > 0 && ` · ${fieldCount !== 1 ? t("fieldsPlural", { count: fieldCount }) : t("fields", { count: 1 })}`}
            {workflow.rules.length > 0 && ` · ${workflow.rules.length !== 1 ? t("rulesPlural", { count: workflow.rules.length }) : t("rules", { count: 1 })}`}
          </div>
        </div>
      </div>
      <div className="px-5 py-3 border-t border-border">
        <Link href={`/workflows/${workflow.id}/edit`}>
          <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs">
            <Pencil className="h-3.5 w-3.5" />
            {workflow.status === "draft" ? tCommon("continueEditing") : tCommon("editWorkflow")}
          </Button>
        </Link>
      </div>
    </div>
  );
}

export function WorkflowTile({ workflow }: { workflow: Workflow }) {
  if (workflow.deployedAt && workflow.apiStats) return <DeployedTile workflow={workflow} />;
  return <InactiveTile workflow={workflow} />;
}
