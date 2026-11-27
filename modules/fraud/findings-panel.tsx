"use client";

import { AlertTriangle, CheckCircle2, Eye, ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { groupFindingsByTier } from "./helpers";
import type { FraudAnalysis, FraudFinding, FraudSeverity } from "./types";

const SEVERITY_STYLE: Record<FraudSeverity, string> = {
  clean: "bg-pass-wash text-pass-ink border-pass/30",
  low: "bg-selected text-ink-2 border-line",
  medium: "bg-warn-wash text-warn-ink border-warn/35",
  high: "bg-fail-wash text-fail-ink border-fail/35",
  critical: "bg-fail text-white border-fail",
};

export function FindingsPanel({
  analysis,
  selectedFinding,
  onSelectFinding,
}: {
  analysis: FraudAnalysis;
  selectedFinding: FraudFinding | null;
  onSelectFinding: (finding: FraudFinding) => void;
}) {
  const t = useTranslations("fraud");
  const grouped = groupFindingsByTier(analysis.findings);

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-xl border border-line bg-raised p-4 shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-ink-3">
              {t("riskScore")}
            </p>
            <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">
              {analysis.risk_score}
              <span className="text-sm font-normal text-ink-3"> / 100</span>
            </p>
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase",
              SEVERITY_STYLE[analysis.severity],
            )}
          >
            {analysis.severity === "clean" ? (
              <CheckCircle2 className="size-3.5" aria-hidden />
            ) : (
              <ShieldAlert className="size-3.5" aria-hidden />
            )}
            {t(`severity.${analysis.severity}`)}
          </span>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {analysis.short_circuit_recommended ? (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-fail-wash px-2.5 py-1 text-xs font-medium text-fail-ink">
              <AlertTriangle className="size-3.5" aria-hidden />
              {t("shortCircuitRecommended")}
            </span>
          ) : null}
          {analysis.requires_four_eyes ? (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-warn-wash px-2.5 py-1 text-xs font-medium text-warn-ink">
              <Eye className="size-3.5" aria-hidden />
              {t("fourEyesRequired")}
            </span>
          ) : null}
        </div>

        {analysis.explanation ? (
          <p className="mt-3 rounded-lg border border-line bg-panel p-3 text-[13px] leading-relaxed text-ink-2">
            {analysis.explanation}
          </p>
        ) : null}
      </section>

      {analysis.findings.length === 0 ? (
        <div className="rounded-xl border border-line bg-raised p-5 text-[13px] text-ink-3">
          {t("noFindings")}
        </div>
      ) : (
        ([1, 2, 3] as const).map((tier) => {
          const items = grouped[tier];
          if (items.length === 0) return null;
          return (
            <section
              key={tier}
              className="flex flex-col gap-2 rounded-xl border border-line bg-raised p-4 shadow-panel"
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-3">
                {t(`tier.${tier}`)}
              </h2>
              <div className="flex flex-col gap-2">
                {items.map((item) => {
                  const isSelected = selectedFinding === item;
                  return (
                    <button
                      key={`${item.code}-${item.page ?? 0}-${item.detail}`}
                      type="button"
                      onClick={() => onSelectFinding(item)}
                      className={cn(
                        "flex w-full cursor-pointer flex-col gap-1 rounded-lg border p-3 text-start transition-colors",
                        isSelected
                          ? "border-accent bg-selected"
                          : "border-line bg-panel hover:bg-hover",
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[13px] font-semibold text-ink">{item.title}</span>
                        <span
                          className={cn(
                            "rounded px-1.5 py-0.5 font-mono text-2xs uppercase",
                            SEVERITY_STYLE[item.severity],
                          )}
                        >
                          {item.severity}
                        </span>
                      </div>
                      <p className="text-xs leading-relaxed text-ink-2">{item.detail}</p>
                      <div className="flex flex-wrap items-center gap-2 pt-0.5 font-mono text-2xs text-ink-4">
                        <span>{item.code}</span>
                        <span>· {item.detector}</span>
                        {item.page ? <span>· p.{item.page}</span> : null}
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })
      )}
    </div>
  );
}
