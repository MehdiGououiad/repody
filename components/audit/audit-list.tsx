"use client";

import { ChevronLeft, ChevronRight, Download, Search, X } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useQueryStates } from "nuqs";
import { useState, useTransition } from "react";
import { useDebouncedCallback } from "use-debounce";
import { RunRows } from "@/components/audit/run-row";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import {
  auditSearchParams,
  auditsExportHref,
  auditsQuery,
  OUTCOMES,
  PAGE_SIZE,
} from "@/lib/audits/search-params";
import { cn } from "@/lib/utils";

function SearchField({ value, onChange }: { value: string; onChange: (q: string) => void }) {
  const t = useTranslations("audits.filters");
  const [text, setText] = useState(value);
  const commit = useDebouncedCallback(onChange, 250);
  return (
    <label className="flex h-7 min-w-0 flex-1 items-center gap-2 rounded-md px-2 text-ink-3 transition-colors duration-100 focus-within:bg-hover hover:bg-hover sm:max-w-xs">
      <Search className="size-3.5 shrink-0" aria-hidden />
      <span className="sr-only">{t("searchPlaceholder")}</span>
      <input
        type="search"
        autoComplete="off"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          commit(event.target.value);
        }}
        placeholder={t("searchPlaceholder")}
        className="h-full min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-4 focus-visible:outline-none"
      />
    </label>
  );
}

/** Every finished run, searched, filtered and paged by the API; the filters live in the URL. */
export function AuditList() {
  const t = useTranslations("audits");
  const format = useFormatter();
  // URL changes run in a transition: the current page stays while the next one loads.
  const [loading, startTransition] = useTransition();
  const [search, setSearch] = useQueryStates(auditSearchParams, {
    history: "replace",
    startTransition,
  });
  const { audits, total } = $api.useSuspenseQuery("get", "/v1/audits", {
    params: { query: auditsQuery(search) },
  }).data;
  const { workflows } = $api.useSuspenseQuery("get", "/v1/workflows").data;
  const filter = (patch: Partial<typeof search>) => void setSearch({ ...patch, page: 1 });
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = Boolean(search.outcome || search.workflow || search.day || search.q);

  const chips: { key: string; label: string; clear: () => void }[] = [];
  if (search.workflow) {
    chips.push({
      key: "workflow",
      label: workflows.find((w) => w.id === search.workflow)?.name ?? search.workflow,
      clear: () => filter({ workflow: null }),
    });
  }
  if (search.day) {
    chips.push({
      key: "day",
      label: format.dateTime(search.day, { dateStyle: "medium", timeZone: "UTC" }),
      clear: () => filter({ day: null }),
    });
  }

  return (
    <div className="flex flex-col">
      <div className="sticky top-11 z-10 flex flex-wrap items-center gap-1 border-b border-line bg-panel px-3 py-1.5 md:px-4">
        <fieldset
          className="flex items-center gap-0.5 m-0 min-w-0 border-0 p-0"
          aria-label={t("filters.status")}
        >
          {[null, ...OUTCOMES].map((outcome) => (
            <button
              key={outcome ?? "all"}
              type="button"
              aria-pressed={search.outcome === outcome}
              onClick={() => filter({ outcome })}
              className="flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2 text-sm font-medium text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink aria-pressed:bg-selected aria-pressed:text-ink"
            >
              {outcome ? <StatusGlyph status={outcome} /> : null}
              {outcome ? t(`status.${outcome}`) : t("filters.allStatuses")}
            </button>
          ))}
        </fieldset>
        <span className="mx-1 hidden h-4 w-px bg-line sm:block" aria-hidden />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="text-sm">
              {t("filters.workflow")}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-80 w-64">
            <DropdownMenuLabel>{t("filters.workflow")}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {workflows.map((workflow) => (
              <DropdownMenuCheckboxItem
                key={workflow.id}
                checked={search.workflow === workflow.id}
                onCheckedChange={(on) => filter({ workflow: on ? workflow.id : null })}
              >
                <span className="truncate">{workflow.name}</span>
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {chips.map((chip) => (
          <button
            key={chip.key}
            type="button"
            onClick={chip.clear}
            className="flex h-6 cursor-pointer items-center gap-1 rounded-md bg-selected ps-2 pe-1.5 text-xs font-medium text-ink-2 transition-colors duration-100 hover:text-ink"
          >
            {chip.label}
            <X className="size-3" aria-hidden />
            <span className="sr-only">{t("filters.clearAll")}</span>
          </button>
        ))}
        <div className="ms-auto flex flex-1 items-center justify-end gap-1">
          <SearchField value={search.q} onChange={(q) => filter({ q })} />
          <Button asChild variant="ghost" size="icon-sm" title={t("exportCsv")}>
            <a href={auditsExportHref(search)} download aria-label={t("exportCsv")}>
              <Download />
            </a>
          </Button>
        </div>
      </div>

      <div className={cn("transition-opacity duration-150", loading && "opacity-60")}>
        {audits.length ? (
          <RunRows audits={audits} />
        ) : (
          <div className="flex flex-col items-center gap-3 px-6 py-20 text-center">
            <p className="text-sm font-medium text-ink">
              {filtered ? t("table.empty") : t("emptyTitle")}
            </p>
            <p className="max-w-sm text-sm text-ink-3">
              {filtered ? t("emptyFilteredHint") : t("emptyHint")}
            </p>
            {filtered ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => filter({ outcome: null, workflow: null, day: null, q: "" })}
              >
                {t("filters.clearAll")}
              </Button>
            ) : (
              <Button asChild size="sm">
                <Link href="/workflows">{t("emptyCta")}</Link>
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="flex h-11 items-center justify-between gap-2 border-t border-line px-4 text-xs text-ink-3 md:px-5">
        <span className="tabular-nums">{t("table.total", { total })}</span>
        {pages > 1 ? (
          <div className="flex items-center gap-1">
            <span className="me-1 tabular-nums">
              {t("table.page", { page: search.page, pages })}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => void setSearch({ page: search.page - 1 })}
              disabled={search.page <= 1}
              aria-label={t("table.previous")}
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => void setSearch({ page: search.page + 1 })}
              disabled={search.page >= pages}
              aria-label={t("table.next")}
            >
              <ChevronRight />
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
