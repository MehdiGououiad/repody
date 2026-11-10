"use client";

import { useTable } from "@tanstack/react-table";
import { Inbox } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  AUDIT_COLUMN_CLASSES,
  auditTableFeatures,
  useAuditColumns,
} from "@/components/audit/audit-columns";
import { DataTable } from "@/components/ui/data-table";
import type { Audit } from "@/lib/types";

/** The dashboard's latest audits, with the columns of the audits page. */
export function RecentAuditsTable({ audits }: { audits: Audit[] }) {
  const t = useTranslations("audits.table");
  const tDashboard = useTranslations("dashboard.recent");
  const table = useTable({
    features: auditTableFeatures,
    columns: useAuditColumns(),
    data: audits,
    getRowId: (audit) => audit.id,
    manualPagination: true,
  });

  return (
    <div className="panel-elevated rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="font-display text-sm font-semibold">{tDashboard("title")}</h3>
      </div>
      <DataTable
        table={table}
        columnClassName={AUDIT_COLUMN_CLASSES}
        empty={
          <span className="inline-flex flex-col items-center gap-2">
            <Inbox className="h-6 w-6 opacity-50" aria-hidden="true" />
            {t("empty")}
          </span>
        }
      />
    </div>
  );
}
