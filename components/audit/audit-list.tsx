"use client";

import { type PaginationState, useTable } from "@tanstack/react-table";
import { ChevronLeft, ChevronRight, Download, Filter, Search, X } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useQueryStates } from "nuqs";
import { useState, useTransition } from "react";
import { useDebouncedCallback } from "use-debounce";
import {
  AUDIT_COLUMN_CLASSES,
  auditTableFeatures,
  useAuditColumns,
} from "@/components/audit/audit-columns";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { $api } from "@/lib/api/browser";
import {
  auditSearchParams,
  auditsExportHref,
  auditsQuery,
  OUTCOMES,
  PAGE_SIZE,
} from "@/lib/audits/search-params";

const ALL = "all";

function SearchInput({ value, onChange }: { value: string; onChange: (q: string) => void }) {
  const t = useTranslations("audits.filters");
  const [text, setText] = useState(value);
  const commit = useDebouncedCallback(onChange, 300);
  return (
    <div className="relative flex-1 min-w-[220px] max-w-md">
      <Label htmlFor="audit-search" className="sr-only">
        {t("searchPlaceholder")}
      </Label>
      <Search
        className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-on-surface-variant"
        aria-hidden="true"
      />
      <Input
        id="audit-search"
        name="audit-search"
        autoComplete="off"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          commit(event.target.value);
        }}
        placeholder={t("searchPlaceholder")}
        className="pl-9"
      />
    </div>
  );
}

/** Finished runs, searched, filtered and paged by the API; the filters live in the URL. */
export function AuditList() {
  const t = useTranslations("audits");
  const format = useFormatter();
  // URL changes run in a transition: React keeps showing the current page while the next one
  // loads (https://nuqs.dev/docs/options#transitions).
  const [loading, startTransition] = useTransition();
  const [search, setSearch] = useQueryStates(auditSearchParams, {
    history: "replace",
    startTransition,
  });
  const audits = $api.useSuspenseQuery("get", "/v1/audits", {
    params: { query: auditsQuery(search) },
  });
  const { workflows } = $api.useSuspenseQuery("get", "/v1/workflows").data;
  const columns = useAuditColumns();

  const pagination: PaginationState = { pageIndex: search.page - 1, pageSize: PAGE_SIZE };
  const table = useTable({
    features: auditTableFeatures,
    columns,
    data: audits.data.audits,
    rowCount: audits.data.total,
    getRowId: (audit) => audit.id,
    manualPagination: true,
    state: { pagination },
    onPaginationChange: (updater) => {
      const next = typeof updater === "function" ? updater(pagination) : updater;
      void setSearch({ page: next.pageIndex + 1 });
    },
  });

  // Every filter change starts again at the first page.
  const filter = (patch: Partial<typeof search>) => void setSearch({ ...patch, page: 1 });
  const total = audits.data.total;
  const workflowName = workflows.find((w) => w.id === search.workflow)?.name ?? search.workflow;
  const chips: { key: string; label: string; clear: () => void }[] = [];
  if (search.outcome) {
    chips.push({
      key: "outcome",
      label: `${t("filters.status")}: ${t(`status.${search.outcome}`)}`,
      clear: () => filter({ outcome: null }),
    });
  }
  if (search.workflow) {
    chips.push({
      key: "workflow",
      label: `${t("filters.workflow")}: ${workflowName}`,
      clear: () => filter({ workflow: null }),
    });
  }
  if (search.day) {
    const day = format.dateTime(search.day, { dateStyle: "medium", timeZone: "UTC" });
    chips.push({
      key: "day",
      label: `${t("filters.day")}: ${day}`,
      clear: () => filter({ day: null }),
    });
  }

  return (
    <div className="panel-elevated rounded-xl flex flex-col">
      <div className="flex flex-wrap items-center gap-2 p-4 border-b border-border/70">
        <SearchInput value={search.q} onChange={(q) => filter({ q })} />
        <Select
          value={search.outcome ?? ALL}
          onValueChange={(v) =>
            filter({ outcome: v === ALL ? null : (v as (typeof OUTCOMES)[number]) })
          }
        >
          <SelectTrigger className="w-[160px]" aria-label={t("filters.status")}>
            <SelectValue placeholder={t("filters.status")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("filters.allStatuses")}</SelectItem>
            {OUTCOMES.map((outcome) => (
              <SelectItem key={outcome} value={outcome}>
                {t(`status.${outcome}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={search.workflow ?? ALL}
          onValueChange={(v) => filter({ workflow: v === ALL ? null : v })}
        >
          <SelectTrigger className="w-[220px]" aria-label={t("filters.workflow")}>
            <SelectValue placeholder={t("filters.workflow")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("filters.allWorkflows")}</SelectItem>
            {workflows.map((workflow) => (
              <SelectItem key={workflow.id} value={workflow.id}>
                {workflow.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button asChild variant="outline" size="sm" className="gap-1.5">
          <a href={auditsExportHref(search)} download>
            <Download className="h-3.5 w-3.5" />
            {t("exportCsv")}
          </a>
        </Button>
        <div className="ml-auto text-xs text-on-surface-variant tabular-nums">
          {t("table.total", { total })}
        </div>
      </div>

      {chips.length ? (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-surface-container-low">
          <Filter className="h-3.5 w-3.5 text-on-surface-variant" aria-hidden="true" />
          {chips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={chip.clear}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-0.5 text-xs font-medium hover:bg-muted transition-colors"
            >
              {chip.label}
              <X className="h-3 w-3" aria-hidden="true" />
            </button>
          ))}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs"
            onClick={() => filter({ outcome: null, workflow: null, day: null })}
          >
            {t("filters.clearAll")}
          </Button>
        </div>
      ) : null}

      <div className={loading ? "opacity-60 transition-opacity" : undefined}>
        <DataTable table={table} columnClassName={AUDIT_COLUMN_CLASSES} empty={t("table.empty")} />
      </div>

      {table.getPageCount() > 1 ? (
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border/70 text-xs text-on-surface-variant">
          <span className="tabular-nums">
            {t("table.page", { page: search.page, pages: table.getPageCount() })}
          </span>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            aria-label={t("table.previous")}
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            aria-label={t("table.next")}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      ) : null}
    </div>
  );
}
