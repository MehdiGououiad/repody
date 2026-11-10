"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  type RowSelectionState,
  rowSelectionFeature,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { Activity, ChevronRight, FileEdit, Play, Trash2, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { toast } from "sonner";
import { DateTime } from "@/components/shared/date-time";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { $api } from "@/lib/api/browser";
import { errorMessage } from "@/lib/query/get-query-client";
import type { Workflow, WorkflowStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const features = tableFeatures({ rowSelectionFeature });
const COLUMNS = [{ id: "workflow" }];

const STATUS: Record<WorkflowStatus, { variant: "success" | "outline"; Icon: typeof Play }> = {
  active: { variant: "success", Icon: Play },
  draft: { variant: "outline", Icon: FileEdit },
};

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-on-surface-variant uppercase tracking-wider">{label}</div>
      <div className="text-sm font-medium mt-0.5 inline-flex items-center gap-0.5 justify-center truncate">
        {children}
      </div>
    </div>
  );
}

function WorkflowCard({
  workflow,
  selected,
  onSelect,
}: {
  workflow: Workflow;
  selected: boolean;
  onSelect: (selected: boolean) => void;
}) {
  const t = useTranslations("workflows");
  const tCommon = useTranslations("common");
  const format = useFormatter();
  const { variant, Icon } = STATUS[workflow.status];

  return (
    <div
      className={cn(
        "panel-elevated rounded-xl p-5 transition-[border-color,box-shadow] duration-200 group flex items-start gap-3",
        selected ? "border-accent-blue ring-1 ring-accent-blue/25" : "hover:border-accent-blue/20"
      )}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={(event) => onSelect(event.target.checked)}
        aria-label={t("delete.selectWorkflow", { name: workflow.name })}
        className="mt-1 size-4 shrink-0 rounded border-border cursor-pointer accent-primary"
      />
      <Link href={`/workflows/${workflow.id}/edit`} className="flex-1 min-w-0 flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-on-surface group-hover:text-primary transition-colors truncate">
              {workflow.name}
            </h3>
            <p className="text-xs text-on-surface-variant mt-1 line-clamp-2">
              {workflow.description}
            </p>
          </div>
          <Badge variant={variant} className="shrink-0">
            <Icon className="h-3 w-3" />
            {t(`status.${workflow.status}`)}
          </Badge>
        </div>

        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-border text-center">
          <Stat label={t("card.lastRun")}>
            {workflow.lastRun ? <DateTime value={workflow.lastRun} /> : "—"}
          </Stat>
          <Stat label={t("card.success")}>
            {workflow.successRate > 0 ? (
              <span
                className={cn(
                  "inline-flex items-center gap-0.5 font-semibold",
                  workflow.successRate > 0.95 ? "text-success" : "text-warning-strong"
                )}
              >
                <TrendingUp className="h-3 w-3" />
                {format.number(workflow.successRate, {
                  style: "percent",
                  maximumFractionDigits: 1,
                })}
              </span>
            ) : (
              "—"
            )}
          </Stat>
          <Stat label={t("card.runs")}>
            <Activity className="h-3 w-3 text-on-surface-variant" />
            {format.number(workflow.totalRuns)}
          </Stat>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-on-surface-variant">
            {tCommon("owner")}: {workflow.owner}
          </span>
          <span className="inline-flex items-center gap-1 text-primary opacity-0 group-hover:opacity-100 transition-opacity font-medium">
            {tCommon("open")}
            <ChevronRight className="h-3 w-3" />
          </span>
        </div>
      </Link>
    </div>
  );
}

/** Workflow cards, prefetched by the page; selected ones can be deleted (archived) together. */
export function WorkflowsList() {
  const t = useTranslations("workflows");
  const tCommon = useTranslations("common");
  const queryClient = useQueryClient();
  const { workflows } = $api.useSuspenseQuery("get", "/v1/workflows").data;
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const table = useTable({
    features,
    columns: COLUMNS,
    data: workflows,
    getRowId: (workflow) => workflow.id,
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
  });
  const selected = table.getSelectedRowModel().rows.map((row) => row.original);

  const remove = $api.useMutation("post", "/v1/workflows/bulk-delete", {
    onSuccess: (_data, { body }) => {
      toast.success(t("delete.success", { count: body.ids.length }));
      setRowSelection({});
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/workflows"] });
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error, tCommon("saveFailed"))),
  });

  if (workflows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-accent-blue/30 bg-surface-container-lowest/80 p-12 text-center panel-elevated">
        <p className="text-sm text-on-surface-variant">{t("delete.empty")}</p>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-3 px-1">
        <label className="inline-flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer select-none">
          <input
            type="checkbox"
            checked={table.getIsAllRowsSelected()}
            ref={(el) => {
              if (el) el.indeterminate = table.getIsSomeRowsSelected();
            }}
            onChange={table.getToggleAllRowsSelectedHandler()}
            className="size-4 rounded border-border accent-primary cursor-pointer"
          />
          {t("delete.selectAll")}
        </label>
        {selected.length > 0 ? (
          <>
            <span className="text-xs text-on-surface-variant">
              {t("delete.selected", { count: selected.length })}
            </span>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={remove.isPending}
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t("delete.deleteSelected")}
            </Button>
          </>
        ) : null}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {table.getRowModel().rows.map((row) => (
          <WorkflowCard
            key={row.id}
            workflow={row.original}
            selected={row.getIsSelected()}
            onSelect={(value) => row.toggleSelected(value)}
          />
        ))}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={() => remove.mutate({ body: { ids: selected.map((w) => w.id) } })}
        title={t("delete.confirmTitle", { count: selected.length })}
        description={
          selected.length <= 3
            ? t("delete.confirmDescriptionNamed", { names: selected.map((w) => w.name).join(", ") })
            : t("delete.confirmDescription", { count: selected.length })
        }
        confirmLabel={t("delete.confirmButton")}
      />
    </>
  );
}
