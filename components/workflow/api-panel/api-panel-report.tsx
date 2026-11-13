"use client";

import { ArrowUpRight, ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ReportBody, ReportVerdict } from "@/components/audit/report";
import { Button } from "@/components/ui/button";
import type { RunAuditDetail } from "@/lib/types";

/** The report of a test run started from the API panel, with the way to its full page. */
export function ApiRunReportScreen({
  report,
  onBack,
}: {
  report: RunAuditDetail;
  onBack: () => void;
}) {
  const t = useTranslations("workflows.builder.api");
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-2">
        <Button variant="ghost" size="sm" onClick={onBack} className="-ms-2">
          <ChevronLeft />
          {t("backToApi")}
        </Button>
        <Button variant="ghost" size="sm" render={<Link href={`/audits/${report.id}`} />}>
          {t("viewFullReport")}
          <ArrowUpRight />
        </Button>
      </div>
      <ReportVerdict audit={report} />
      <ReportBody audit={report} />
    </div>
  );
}
