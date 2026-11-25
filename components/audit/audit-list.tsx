"use client";

import { Button as ButtonPrimitive } from "@ui-sdk/react/button";
import { ChevronLeft, ChevronRight, Download, ListFilter, X } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useQueryStates } from "nuqs";
import { useRef, useState, useTransition } from "react";
import { useDebouncedCallback } from "use-debounce";
import { RunGroups } from "@/components/audit/run-row";
import { ListKeysHint, useListKeys } from "@/components/layout/list-keys";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/ui/input";
import {
  Menu,
  MenuCheck,
  MenuContent,
  MenuGroup,
  MenuGroupLabel,
  MenuTrigger,
} from "@/components/ui/menu";
import { SegmentedControl, SegmentedControlOption } from "@/components/ui/segmented-control";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { Tooltip } from "@/components/ui/tooltip";
import { $api } from "@/lib/api/browser";
import {
  auditSearchParams,
  auditsExportHref,
  auditsQuery,
  OUTCOMES,
  PAGE_SIZE,
} from "@/lib/audits/search-params";
import { cn } from "@/lib/utils";

const LIVE_MS = 10_000;

/** The search box: debounced into the URL, and reset when the URL changes from elsewhere
 * (Clear filters, back), never while the person types. */
function SearchField({ value, onChange }: { value: string; onChange: (q: string) => void }) {
  const t = useTranslations("audits.filters");
  const [text, setText] = useState(value);
  const [sent, setSent] = useState(value);
  const [seen, setSeen] = useState(value);
  if (value !== seen) {
    setSeen(value);
    if (value !== sent) {
      setSent(value);
      setText(value);
    }
  }
  const commit = useDebouncedCallback((q: string) => {
    setSent(q);
    onChange(q);
  }, 250);
  return (
    <SearchInput
      label={t("searchPlaceholder")}
      clearLabel={t("clearSearch")}
      value={text}
      onValueChange={(next: string) => {
        setText(next);
        commit(next);
      }}
    />
  );
}

/** Every finished run, live, filtered and paged by the API; the filters live in the URL. */
export function AuditList() {
  const t = useTranslations("audits");
  const format = useFormatter();
  const listRef = useRef<HTMLDivElement>(null);
  useListKeys(listRef);
  const [loading, startTransition] = useTransition();
  const [search, setSearch] = useQueryStates(auditSearchParams, {
    history: "replace",
    startTransition,
  });
  const { audits, total } = $api.useSuspenseQuery(
    "get",
    "/v1/audits",
    { params: { query: auditsQuery(search) } },
    { refetchInterval: search.page === 1 ? LIVE_MS : false },
  ).data;
  const { workflows } = $api.useSuspenseQuery("get", "/v1/workflows").data;
  const filter = (patch: Partial<typeof search>) => void setSearch({ ...patch, page: 1 });
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = Boolean(search.outcome || search.workflow || search.day || search.q);

  const chips: { key: string; label: string; clear: () => void }[] = [];
  if (search.outcome === "review") {
    chips.push({
      key: "outcome",
      label: t("filters.review"),
      clear: () => filter({ outcome: null }),
    });
  }
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
    <div className="flex min-h-[calc(100dvh-3.5rem)] flex-col">
      <div className="sticky top-[41px] z-10 flex items-center gap-1.5 border-b border-line bg-panel/90 px-3 py-1.5 backdrop-blur-md md:px-4">
        <SegmentedControl
          aria-label={t("filters.status")}
          value={search.outcome === "review" ? null : (search.outcome ?? "all")}
          onValueChange={(value) =>
            filter({
              outcome: value === "all" || !value ? null : (value as (typeof OUTCOMES)[number]),
            })
          }
        >
          <SegmentedControlOption value="all">{t("filters.allStatuses")}</SegmentedControlOption>
          {OUTCOMES.map((outcome) => (
            <SegmentedControlOption key={outcome} value={outcome}>
              <StatusGlyph status={outcome} />
              <span className="max-sm:sr-only">{t(`status.${outcome}`)}</span>
            </SegmentedControlOption>
          ))}
        </SegmentedControl>
        <Menu>
          <MenuTrigger
            render={
              <Button variant="ghost" size="sm">
                <ListFilter />
                {t("filters.workflow")}
              </Button>
            }
          />
          <MenuContent align="start" className="max-h-80 w-64">
            <MenuGroup>
              <MenuGroupLabel>{t("filters.workflow")}</MenuGroupLabel>
              {workflows.map((workflow) => (
                <MenuCheck
                  key={workflow.id}
                  value={workflow.id}
                  checked={search.workflow === workflow.id}
                  closeOnSelect
                  onCheckedChange={(on) => filter({ workflow: on ? workflow.id : null })}
                >
                  <span className="truncate">{workflow.name}</span>
                </MenuCheck>
              ))}
            </MenuGroup>
          </MenuContent>
        </Menu>
        {chips.map((chip) => (
          <ButtonPrimitive
            key={chip.key}
            onClick={chip.clear}
            className="flex h-6 cursor-pointer items-center gap-1 rounded-md bg-accent-wash ps-2 pe-1.5 text-xs font-medium text-accent-ink transition-opacity duration-100 hover:opacity-80"
          >
            {chip.label}
            <X className="size-3" aria-hidden />
            <span className="sr-only">{t("filters.remove")}</span>
          </ButtonPrimitive>
        ))}
        <div className="ms-auto flex flex-1 items-center justify-end gap-1">
          <SearchField value={search.q} onChange={(q) => filter({ q })} />
          <Tooltip label={t("exportCsv")}>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("exportCsv")}
              // oxlint-disable-next-line jsx-a11y/control-has-associated-label -- the label is on the Button that renders this element.
              render={<a href={auditsExportHref(search)} download />}
            >
              <Download />
            </Button>
          </Tooltip>
        </div>
      </div>

      <div
        ref={listRef}
        className={cn("flex-1 transition-opacity duration-150", loading && "opacity-60")}
      >
        {audits.length ? (
          <RunGroups audits={audits} stickyTop="top-[82px]" />
        ) : (
          <div className="flex flex-col items-center gap-2 px-6 py-24 text-center">
            <p className="text-[13px] font-medium text-ink">
              {filtered ? t("table.empty") : t("emptyTitle")}
            </p>
            <p className="max-w-sm text-[13px] text-ink-3">
              {filtered ? t("emptyFilteredHint") : t("emptyHint")}
            </p>
            {filtered ? (
              <Button
                className="mt-2"
                onClick={() => filter({ outcome: null, workflow: null, day: null, q: "" })}
              >
                {t("filters.clearAll")}
              </Button>
            ) : (
              <Button className="mt-2" variant="primary" render={<Link href="/workflows" />}>
                {t("emptyCta")}
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="sticky bottom-0 flex h-9 items-center justify-between gap-2 border-t border-line bg-panel/90 px-4 text-xs text-ink-3 backdrop-blur-md md:px-5">
        <span className="flex items-center gap-3 tabular-nums">
          {t("table.total", { total })}
          <ListKeysHint />
        </span>
        {pages > 1 ? (
          <div className="flex items-center gap-1">
            <span className="me-1 tabular-nums">
              {t("table.page", { page: search.page, pages })}
            </span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => void setSearch({ page: search.page - 1 })}
              disabled={search.page <= 1}
              aria-label={t("table.previous")}
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="ghost"
              size="icon-xs"
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
