"use client";

import { createColumnHelper, rowPaginationFeature, tableFeatures } from "@tanstack/react-table";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useMemo } from "react";
import { AuditStatusBadge } from "@/components/shared/audit-status-badge";
import { DateTime } from "@/components/shared/date-time";
import type { Audit } from "@/lib/types";

/** Audits are paged by the API (`manualPagination`): the table shows the page it is given. */
export const auditTableFeatures = tableFeatures({ rowPaginationFeature });
const column = createColumnHelper<typeof auditTableFeatures, Audit>();

export const AUDIT_COLUMN_CLASSES: Record<string, string> = {
  rows: "text-right font-mono text-xs tabular-nums",
  timestamp: "text-sm text-on-surface-variant tabular-nums",
  workflowName: "text-sm",
};

/** The columns every audit table shows: id (a link to the report), outcome, workflow, when. */
export function useAuditColumns() {
  const t = useTranslations("audits.table");
  const format = useFormatter();
  return useMemo(
    () =>
      column.columns([
        column.accessor("id", {
          header: t("id"),
          cell: (info) => (
            <Link
              href={`/audits/${info.getValue()}`}
              className="font-mono text-xs text-primary hover:underline"
            >
              {info.getValue()}
            </Link>
          ),
        }),
        column.accessor("status", {
          header: t("status"),
          cell: (info) => (
            <AuditStatusBadge
              status={info.getValue()}
              failedCount={info.row.original.failedRules}
            />
          ),
        }),
        column.accessor("workflowName", { header: t("workflow") }),
        column.accessor("timestamp", {
          header: t("timestamp"),
          cell: (info) => <DateTime value={info.getValue()} />,
        }),
        column.accessor("rows", {
          header: t("rows"),
          cell: (info) => format.number(info.getValue()),
        }),
      ]),
    [t, format]
  );
}
