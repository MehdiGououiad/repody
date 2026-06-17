"use client";

import { FileText, ShieldCheck } from "lucide-react";
import type { RunAuditDetail } from "@/lib/types/audit";
import { RunStatusBanner } from "./report-banner";
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

export function RunReportCore({
  audit,
  locale = "en",
  labels,
  subtitle,
}: {
  audit: RunAuditDetail;
  locale?: string;
  labels?: RunReportLabels;
  subtitle?: string;
}) {
  return (
    <div className="space-y-6">
      <RunStatusBanner audit={audit} labels={labels} subtitle={subtitle} />
      <RunDetailedReportSections audit={audit} locale={locale} labels={labels} />
    </div>
  );
}

export {
  ConfidenceBar,
  formatFieldValue,
  type RunReportLabels,
} from "./report-shared";
export { RunStatusBanner } from "./report-banner";
export {
  RunDocFieldsList,
  RunDocFieldsTable,
  RunFieldsList,
} from "./report-fields";
export {
  RunDetailedRuleCard,
  RunRuleResultsDetailed,
  RunRuleResultsSummary,
} from "./report-rules";
