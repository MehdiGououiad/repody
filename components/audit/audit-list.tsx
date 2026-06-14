"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Search, Filter, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { useQueryParam } from "@/lib/hooks/use-query-param";
import type { Audit, AuditStatus } from "@/lib/types";

function AuditSearchInput({
  id,
  initialValue,
  placeholder,
  onQueryChange,
}: {
  id: string;
  initialValue: string;
  placeholder: string;
  onQueryChange: (value: string | null) => void;
}) {
  const [value, setValue] = useState(initialValue);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (value !== initialValue) onQueryChange(value || null);
    }, 300);
    return () => window.clearTimeout(handle);
  }, [initialValue, onQueryChange, value]);

  return (
    <Input
      id={id}
      name="audit-search"
      autoComplete="off"
      value={value}
      onChange={(event) => setValue(event.target.value)}
      placeholder={placeholder}
      className="pl-9"
    />
  );
}

export function AuditList({ audits }: { audits: Audit[] }) {
  const locale = useLocale();
  const t = useTranslations("audits");
  const tCommon = useTranslations("common");

  const [urlQuery, setUrlQuery] = useQueryParam("q");
  const [status, setStatus] = useQueryParam("status", "all");
  const [workflow, setWorkflow] = useQueryParam("workflow", "all");
  const [entity, setEntity] = useQueryParam("entity", "all");

  const workflowOptions = useMemo(
    () =>
      Array.from(new Set(audits.map((a) => a.workflowName))).sort((a, b) =>
        a.localeCompare(b, locale)
      ),
    [audits, locale]
  );
  const entityOptions = useMemo(
    () =>
      Array.from(new Set(audits.map((a) => a.entity))).sort((a, b) =>
        a.localeCompare(b, locale)
      ),
    [audits, locale]
  );

  const filtered = useMemo(() => {
    return audits.filter((a) => {
      if (status !== "all" && a.status !== status) return false;
      if (workflow !== "all" && a.workflowName !== workflow) return false;
      if (entity !== "all" && a.entity !== entity) return false;
      if (urlQuery) {
        const q = urlQuery.toLowerCase();
        if (
          !a.id.toLowerCase().includes(q) &&
          !a.entity.toLowerCase().includes(q) &&
          !a.workflowName.toLowerCase().includes(q)
        )
          return false;
      }
      return true;
    });
  }, [audits, status, workflow, entity, urlQuery]);

  const activeFilters = [
    status !== "all" && {
      key: "status",
      label: `${t("filters.status")}: ${t(`status.${status as AuditStatus}`)}`,
      clear: () => setStatus(null),
    },
    workflow !== "all" && {
      key: "workflow",
      label: `${t("filters.workflow")}: ${workflow}`,
      clear: () => setWorkflow(null),
    },
    entity !== "all" && {
      key: "entity",
      label: `${t("filters.entity")}: ${entity}`,
      clear: () => setEntity(null),
    },
  ].filter(Boolean) as { key: string; label: string; clear: () => void }[];

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleString(locale, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

  const searchId = "audit-list-search";

  return (
    <div className="panel-elevated rounded-xl flex flex-col">
      <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border/70">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Label htmlFor={searchId} className="sr-only">
            {t("filters.searchPlaceholder")}
          </Label>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-on-surface-variant" aria-hidden="true" />
          <AuditSearchInput
            key={urlQuery}
            id={searchId}
            initialValue={urlQuery}
            placeholder={t("filters.searchPlaceholder")}
            onQueryChange={setUrlQuery}
          />
        </div>
        <Select value={status} onValueChange={(v) => setStatus(v === "all" ? null : v)}>
          <SelectTrigger className="w-[160px]" aria-label={t("filters.status")}>
            <SelectValue placeholder={t("filters.status")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("filters.allStatuses")}</SelectItem>
            <SelectItem value="passed">{t("status.passed")}</SelectItem>
            <SelectItem value="failed">{t("status.failed")}</SelectItem>
            <SelectItem value="warning">{t("status.warning")}</SelectItem>
            <SelectItem value="running">{t("status.running")}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={workflow} onValueChange={(v) => setWorkflow(v === "all" ? null : v)}>
          <SelectTrigger className="w-[220px]" aria-label={t("filters.workflow")}>
            <SelectValue placeholder={t("filters.workflow")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("filters.allWorkflows")}</SelectItem>
            {workflowOptions.map((w) => (
              <SelectItem key={w} value={w}>
                {w}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={entity} onValueChange={(v) => setEntity(v === "all" ? null : v)}>
          <SelectTrigger className="w-[180px]" aria-label={t("filters.entity")}>
            <SelectValue placeholder={t("filters.entity")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("filters.allEntities")}</SelectItem>
            {entityOptions.map((e) => (
              <SelectItem key={e} value={e}>
                {e}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="ml-auto text-xs text-on-surface-variant tabular-nums">
          {t("table.filtered", {
            filtered: filtered.length,
            total: audits.length,
            of: tCommon("of"),
          })}
        </div>
      </div>

      {activeFilters.length ? (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-surface-container-low">
          <Filter className="h-3.5 w-3.5 text-on-surface-variant" aria-hidden="true" />
          {activeFilters.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={f.clear}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-0.5 text-xs font-medium hover:bg-muted transition-colors"
            >
              {f.label}
              <X className="h-3 w-3" aria-hidden="true" />
            </button>
          ))}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs"
            onClick={() => {
              setStatus(null);
              setWorkflow(null);
              setEntity(null);
            }}
          >
            {t("filters.clearAll")}
          </Button>
        </div>
      ) : null}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("table.id")}</TableHead>
            <TableHead>{t("table.status")}</TableHead>
            <TableHead>{t("table.workflow")}</TableHead>
            <TableHead>{t("table.entity")}</TableHead>
            <TableHead>{t("table.timestamp")}</TableHead>
            <TableHead className="text-right">{t("table.rows")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-12 text-on-surface-variant">
                {t("table.empty")}
              </TableCell>
            </TableRow>
          ) : (
            filtered.map((a) => (
              <TableRow key={a.id}>
                <TableCell>
                  <Link
                    href={`/audits/${a.id}`}
                    className="font-mono text-xs hover:underline"
                    style={{ color: "var(--primary-stitch)" }}
                  >
                    {a.id}
                  </Link>
                </TableCell>
                <TableCell>
                  <StatusBadge status={a.status} failedCount={a.failedRules} />
                </TableCell>
                <TableCell className="text-sm">{a.workflowName}</TableCell>
                <TableCell className="text-sm">{a.entity}</TableCell>
                <TableCell className="text-sm text-on-surface-variant tabular-nums">{fmtDate(a.timestamp)}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {a.rows === null ? "—" : formatNumber(a.rows, locale)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
