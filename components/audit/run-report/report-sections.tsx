"use client";

import { FileText, ShieldCheck } from "lucide-react";
import type { RunAuditDetail } from "@/lib/types/audit";
import { RunFieldsList } from "./report-fields";
import { RunRuleResultsDetailed } from "./report-rules";
import { mergeLabels, type RunReportLabels } from "./report-shared";

export function RunDetailedReportSections({
  audit,
  locale,
  labels,
}: {
  audit: RunAuditDetail;
  locale: string;
  labels?: RunReportLabels;
}) {
  const L = mergeLabels(labels);

  return (
    <>
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-on-surface-variant" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            {L.extractedData}
          </h3>
        </div>
        <RunFieldsList audit={audit} locale={locale} labels={labels} />
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-on-surface-variant" aria-hidden="true" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            {L.validationResults}
          </h3>
        </div>
        <div className="space-y-3">
          <RunRuleResultsDetailed audit={audit} labels={labels} size="sm" />
        </div>
      </section>
    </>
  );
}
