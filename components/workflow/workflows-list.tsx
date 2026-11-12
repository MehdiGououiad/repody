"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Trash2, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { toast } from "sonner";
import { When } from "@/components/audit/run-row";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { errorMessage } from "@/lib/query/get-query-client";
import type { Workflow } from "@/lib/types";
import { cn } from "@/lib/utils";

const GRID =
  "grid grid-cols-[14px_14px_minmax(0,1fr)_auto] items-center gap-3 md:grid-cols-[14px_14px_minmax(0,1fr)_72px_72px_96px]";

function WorkflowRow({
  workflow,
  selected,
  selecting,
  onSelect,
}: {
  workflow: Workflow;
  selected: boolean;
  selecting: boolean;
  onSelect: (selected: boolean) => void;
}) {
  const t = useTranslations("workflows");
  const format = useFormatter();
  const live = workflow.status === "active";
  return (
    <li
      className={cn(
        "group relative h-11 px-4 transition-colors duration-100 hover:bg-hover md:px-5",
        GRID,
        selected && "bg-selected hover:bg-selected"
      )}
    >
      <Checkbox
        checked={selected}
        onCheckedChange={(value) => onSelect(value === true)}
        aria-label={t("delete.selectWorkflow", { name: workflow.name })}
        className={cn(
          "z-10 opacity-0 transition-opacity duration-100 focus-visible:opacity-100 group-hover:opacity-100",
          (selected || selecting) && "opacity-100"
        )}
      />
      <StatusGlyph status={live ? "live" : "draft"} label={t(`status.${workflow.status}`)} />
      <Link
        href={`/workflows/${workflow.id}/edit`}
        className="flex min-w-0 items-baseline gap-2 after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:-outline-offset-2 focus-visible:after:outline-focus"
      >
        <span className="truncate text-sm font-medium text-ink">{workflow.name}</span>
        {workflow.description ? (
          <span className="hidden truncate text-sm text-ink-3 lg:inline">
            {workflow.description}
          </span>
        ) : null}
      </Link>
      <span className="hidden text-end text-xs tabular-nums text-ink-3 md:block">
        {t("row.runs", { count: workflow.totalRuns, formatted: format.number(workflow.totalRuns) })}
      </span>
      <span className="hidden text-end text-xs tabular-nums text-ink-3 md:block">
        {workflow.totalRuns
          ? format.number(workflow.successRate, { style: "percent", maximumFractionDigits: 0 })
          : "—"}
      </span>
      <span className="text-end text-xs tabular-nums text-ink-3">
        {workflow.lastRun ? <When value={workflow.lastRun} /> : t("row.neverRun")}
      </span>
    </li>
  );
}

/** Every workflow, newest first; select some to delete (archive) them together. */
export function WorkflowsList() {
  const t = useTranslations("workflows");
  const tCommon = useTranslations("common");
  const queryClient = useQueryClient();
  const { workflows } = $api.useSuspenseQuery("get", "/v1/workflows").data;
  const [selection, setSelection] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const selected = workflows.filter((w) => selection.has(w.id));

  const remove = $api.useMutation("post", "/v1/workflows/bulk-delete", {
    onSuccess: (_data, { body }) => {
      toast.success(t("delete.success", { count: body.ids.length }));
      setSelection(new Set());
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/workflows"] });
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error, tCommon("saveFailed"))),
  });

  if (workflows.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 px-6 py-24 text-center">
        <p className="text-sm font-medium text-ink">{t("emptyTitle")}</p>
        <p className="max-w-sm text-sm text-ink-3">{t("emptyHint")}</p>
        <Button asChild size="sm">
          <Link href="/workflows/new">{tCommon("newWorkflow")}</Link>
        </Button>
      </div>
    );
  }

  const all = selection.size === workflows.length;
  return (
    <>
      <div className={cn("h-8 border-b border-line px-4 text-xs text-ink-3 md:px-5", GRID)}>
        <Checkbox
          checked={all ? true : selection.size ? "indeterminate" : false}
          onCheckedChange={(value) =>
            setSelection(value === true ? new Set(workflows.map((w) => w.id)) : new Set())
          }
          aria-label={t("delete.selectAll")}
        />
        <span />
        <span>{t("columns.name")}</span>
        <span className="hidden text-end md:block">{t("columns.runs")}</span>
        <span className="hidden text-end md:block">{t("columns.passRate")}</span>
        <span className="text-end">{t("columns.lastRun")}</span>
      </div>
      <ul className="divide-y divide-line">
        {workflows.map((workflow) => (
          <WorkflowRow
            key={workflow.id}
            workflow={workflow}
            selected={selection.has(workflow.id)}
            selecting={selection.size > 0}
            onSelect={(on) =>
              setSelection((current) => {
                const next = new Set(current);
                if (on) next.add(workflow.id);
                else next.delete(workflow.id);
                return next;
              })
            }
          />
        ))}
      </ul>

      <AnimatePresence>
        {selection.size ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8, transition: { duration: 0.12 } }}
            transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
            className="sticky bottom-4 z-20 mx-auto mt-4 flex w-fit items-center gap-1 rounded-lg bg-overlay p-1 ps-3 shadow-pop"
          >
            <span className="me-2 text-sm tabular-nums text-ink-2">
              {t("delete.selected", { count: selection.size })}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="text-fail-ink hover:text-fail-ink"
              disabled={remove.isPending}
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 />
              {t("delete.deleteSelected")}
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setSelection(new Set())}
              aria-label={tCommon("cancel")}
            >
              <X />
            </Button>
          </motion.div>
        ) : null}
      </AnimatePresence>

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
