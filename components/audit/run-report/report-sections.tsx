"use client";

import { FileText, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import type { RunAuditDetail } from "@/lib/types";
import { RunFieldsList } from "./report-fields";
import { RunRuleResultsDetailed } from "./report-rules";

/** Extracted fields, then rule results: the report body shown inside other panels. */
export function RunDetailedReportSections({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  return (
    <>
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-on-surface-variant" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("extractedData")}
          </h3>
        </div>
        <RunFieldsList audit={audit} />
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-on-surface-variant" aria-hidden="true" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("validationRules")}
          </h3>
        </div>
        <div className="space-y-3">
          <RunRuleResultsDetailed audit={audit} size="sm" />
        </div>
      </section>
    </>
  );
}
