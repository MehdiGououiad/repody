"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowUpRight, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/shared/status-badge";
import { formatNumber } from "@/lib/utils";
import type { Audit } from "@/lib/types";

interface RecentAuditsTableProps {
  audits: Audit[];
  title?: string;
  limit?: number;
  /** Compose header actions (e.g. view-all link) instead of boolean flags. */
  actions?: React.ReactNode;
}

export function RecentAuditsViewAllAction() {
  const tCommon = useTranslations("common");

  return (
    <Button asChild variant="ghost" size="sm" className="text-accent-blue h-7">
      <Link href="/audits">
        {tCommon("viewAll")}
        <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
      </Link>
    </Button>
  );
}

export function RecentAuditsTable({
  audits,
  title,
  limit,
  actions,
}: RecentAuditsTableProps) {
  const locale = useLocale();
  const t = useTranslations("audits.table");
  const tDashboard = useTranslations("dashboard.recent");
  const heading = title ?? tDashboard("title");
  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleString(locale, {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  const rows = limit ? audits.slice(0, limit) : audits;

  return (
    <div className="panel-elevated rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="font-display text-sm font-semibold">{heading}</h3>
        {actions}
      </div>
      {rows.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-on-surface-variant">
          <Inbox className="h-6 w-6 opacity-50" aria-hidden="true" />
          <p className="text-sm">{t("empty")}</p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-1/5">{t("id")}</TableHead>
              <TableHead className="w-1/5">{t("status")}</TableHead>
              <TableHead className="w-1/5">{t("workflow")}</TableHead>
              <TableHead className="w-1/5">{t("timestamp")}</TableHead>
              <TableHead className="text-right">{t("rows")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((a) => (
              <TableRow key={a.id}>
                <TableCell>
                  <Link
                    href={`/audits/${a.id}`}
                    className="font-mono text-xs text-primary-stitch hover:underline"
                    style={{ color: "var(--primary-stitch)" }}
                  >
                    {a.id}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge status={a.status} failedCount={a.failedRules} />
                </TableCell>
                <TableCell className="text-on-surface-variant text-sm">{a.workflowName}</TableCell>
                <TableCell className="text-on-surface-variant text-sm tabular-nums">{fmtDate(a.timestamp)}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {a.rows === null ? "—" : formatNumber(a.rows, locale)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
