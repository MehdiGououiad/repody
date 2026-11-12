"use client";

import { Download, Printer } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ReportBody, ReportVerdict } from "@/components/audit/report";
import { Page } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import type { RunAuditDetail } from "@/lib/types";

/** One finished run's report; prints as a PDF, exports as CSV (from the API). */
export function RunAuditReport({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  const tNav = useTranslations("nav");
  return (
    <Page
      trail={
        <>
          <Link href="/audits" className="text-ink-3 transition-colors duration-100 hover:text-ink">
            {tNav("audits")}
          </Link>
          <span className="text-ink-4" aria-hidden>
            /
          </span>
        </>
      }
      title={<span className="truncate">{audit.workflowName}</span>}
      actions={
        <div className="no-print flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => window.print()}>
            <Printer />
            {t("exportPdf")}
          </Button>
          <Button asChild variant="ghost" size="sm">
            <a href={`/api/v1/audits/${encodeURIComponent(audit.id)}/export.csv`} download>
              <Download />
              {t("exportCsv")}
            </a>
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-8">
        <div className="flex flex-col gap-1">
          <ReportVerdict audit={audit} />
          <p className="ps-8 font-mono text-xs text-ink-4">{audit.id}</p>
        </div>
        <ReportBody audit={audit} />
      </div>
    </Page>
  );
}
