"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { useTranslations } from "next-intl";
import {
  Loader2,
  PlayCircle,
  FlaskConical,
  Brain,
  Code,
  AlertTriangle,
  RotateCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { syncRuleBodies } from "@/lib/rules/sync-rules";
import { formatApiError } from "@/lib/rules/rule-validation";
import {
  isRuleFailure,
  RuleStatusIcon,
  ruleStatusBorder,
  ruleStatusColor,
  ruleStatusLabel,
  type RuleEvalStatus,
} from "@/lib/rule-status";
import type { SchemaField, WorkflowRule } from "@/lib/types";

interface DryRunResult {
  extracted: { field: string; value: string; matched: boolean }[];
  ruleResults: {
    id: string;
    name: string;
    kind: "logic" | "llm";
    status: RuleEvalStatus;
    detail: string;
  }[];
}

export function DryRunPanel({
  workflowId,
  fields,
  rules,
  sampleName,
}: {
  workflowId: string;
  fields: SchemaField[];
  rules: WorkflowRule[];
  sampleName: string;
}) {
  const t = useTranslations("workflows.builder.dryRun");
  const tCommon = useTranslations("common");
  const [result, setResult] = useState<DryRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [auto, setAuto] = useState(true);
  const [sampleValues, setSampleValues] = useState<Record<string, string>>({});

  const run = useCallback(() => {
    setError(null);
    startTransition(async () => {
      try {
        const payloadFields = fields.map((f) => ({
          ...f,
          sampleValue: sampleValues[f.id]?.trim() || f.sampleValue || undefined,
        }));
        const res = await fetch(`/api/workflows/${workflowId}/dry-run`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ fields: payloadFields, rules: syncRuleBodies(rules) }),
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(formatApiError(text) || `HTTP ${res.status}`);
        }
        const data: DryRunResult = await res.json();
        setResult(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed");
      }
    });
  }, [workflowId, fields, rules, sampleValues]);

  useEffect(() => {
    if (!auto) return;
    const handle = setTimeout(run, 500);
    return () => clearTimeout(handle);
  }, [auto, run]);

  const failed =
    result?.ruleResults.filter((r) => isRuleFailure(r.status)).length ?? 0;
  const passed = result?.ruleResults.filter((r) => r.status === "passed").length ?? 0;
  const skipped =
    result?.ruleResults.filter((r) => r.status === "skipped").length ?? 0;

  return (
    <section className="panel-elevated rounded-xl overflow-hidden flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-accent-blue" />
          <h3 className="font-display text-sm font-semibold">{t("title")}</h3>
        </div>
        <Button
          variant={auto ? "secondary" : "outline"}
          size="sm"
          className="h-7 text-xs"
          onClick={() => setAuto((v) => !v)}
        >
          {auto ? t("autoOn") : t("autoOff")}
        </Button>
      </div>
      <div className="px-4 py-2 border-b border-border bg-surface-container-low flex items-center justify-between text-xs">
        <span className="text-on-surface-variant truncate">
          {t("sample")}: <span className="font-mono">{sampleName || "—"}</span>
        </span>
        <Button variant="ghost" size="sm" onClick={run} disabled={pending} className="h-6 text-xs">
          {pending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <PlayCircle className="h-3 w-3" />
          )}
          {t("run")}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {fields.some((f) => f.name.trim()) && (
          <div>
            <h4 className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant mb-2">
              Sample values (dry-run)
            </h4>
            <div className="space-y-1.5">
              {fields
                .filter((f) => f.name.trim())
                .map((f) => (
                  <div key={f.id} className="flex items-center gap-2 text-xs">
                    <span className="font-mono text-on-surface-variant w-24 truncate shrink-0">
                      {f.name}
                    </span>
                    <Input
                      value={sampleValues[f.id] ?? f.sampleValue ?? ""}
                      onChange={(e) =>
                        setSampleValues((prev) => ({ ...prev, [f.id]: e.target.value }))
                      }
                      placeholder="Optional test value"
                      className="h-7 text-xs font-mono"
                    />
                  </div>
                ))}
            </div>
          </div>
        )}

        {error ? (
          <div className="rounded-lg border border-danger/30 bg-danger/5 p-4 flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-danger shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-danger">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={run}
                disabled={pending}
                className="mt-3 h-7 text-xs gap-1.5"
              >
                <RotateCw className={cn("h-3 w-3", pending && "animate-spin")} />
                {tCommon("retry")}
              </Button>
            </div>
          </div>
        ) : !result && pending ? (
          <div className="text-sm text-on-surface-variant flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("running")}
          </div>
        ) : !result ? (
          <div className="text-sm text-on-surface-variant space-y-1">
            <p>{t("idle")}</p>
            <p className="text-[11px]">{t("idleHint")}</p>
          </div>
        ) : (
          <>
            <div>
              <h4 className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant mb-2">
                {t("extracted")} ({result.extracted.length})
              </h4>
              <div className="space-y-1">
                {result.extracted.map((e) => (
                  <div
                    key={e.field}
                    className="flex items-center justify-between gap-2 text-xs py-1.5 px-2 rounded bg-surface-container-low"
                  >
                    <span className="font-mono text-on-surface-variant truncate">{e.field}</span>
                    <span className="font-mono font-medium text-on-surface">
                      {e.matched ? e.value : "—"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant mb-2 flex items-center justify-between">
                <span>{t("results")}</span>
                <span className="flex gap-1">
                  {failed > 0 ? (
                    <Badge variant="danger" className="text-[9px]">
                      {t("failed", { count: failed })}
                    </Badge>
                  ) : null}
                  {skipped > 0 ? (
                    <Badge variant="secondary" className="text-[9px]">
                      {skipped} skipped
                    </Badge>
                  ) : null}
                  <Badge variant="success" className="text-[9px]">
                    {t("passed", { count: passed })}
                  </Badge>
                </span>
              </h4>
              <div className="space-y-2">
                {result.ruleResults.map((r) => {
                  const KindIcon = r.kind === "llm" ? Brain : Code;
                  const failedRule = isRuleFailure(r.status);
                  return (
                    <div
                      key={r.id}
                      className={cn(
                        "rounded-md border p-2 text-xs",
                        failedRule
                          ? "border-danger/40 bg-danger-soft/30"
                          : ruleStatusBorder(r.status)
                      )}
                    >
                      <div className="flex items-center gap-1.5 font-semibold">
                        <RuleStatusIcon
                          status={r.status}
                          className={cn(
                            "h-3 w-3 shrink-0",
                            ruleStatusColor(r.status)
                          )}
                        />
                        <KindIcon
                          className={cn(
                            "h-3 w-3",
                            r.kind === "llm" ? "text-accent-blue" : "text-on-surface-variant"
                          )}
                        />
                        {r.name}
                        {r.status !== "passed" && r.status !== "failed" && (
                          <Badge variant="secondary" className="text-[8px] ml-auto">
                            {ruleStatusLabel(r.status)}
                          </Badge>
                        )}
                      </div>
                      <p
                        className={cn(
                          "mt-1 text-[11px]",
                          failedRule ? "text-danger-strong" : "text-on-surface-variant"
                        )}
                      >
                        {r.detail}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
