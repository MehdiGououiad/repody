"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useShortcut } from "@ui-sdk/react/shortcuts";
import { toast } from "@ui-sdk/react/toast";
import { Archive, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { When } from "@/components/audit/run-row";
import { useCan } from "@/components/auth/access-context";
import { Gate } from "@/components/auth/gate";
import { ListKeysHint, useListKeys } from "@/components/layout/list-keys";
import { DocChip } from "@/components/shared/doc-chip";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Kbd } from "@/components/ui/kbd";
import { confirmAction } from "@/components/ui/overlays";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { EASE_OUT, rowEnter } from "@/lib/motion";
import { errorMessage } from "@/lib/query/get-query-client";
import type { Workflow } from "@/lib/types";
import { cn } from "@/lib/utils";

const GRID =
  "grid grid-cols-[14px_14px_minmax(0,1fr)_auto] items-center gap-3 md:grid-cols-[14px_14px_minmax(0,1fr)_minmax(0,1fr)_120px_96px]";

function WorkflowRow({
  workflow,
  index,
  selected,
  selecting,
  onSelect,
}: {
  workflow: Workflow;
  index: number;
  selected: boolean;
  selecting: boolean;
  onSelect: (selected: boolean) => void;
}) {
  const t = useTranslations("workflows");
  const format = useFormatter();
  const live = workflow.status === "active";
  return (
    <motion.li
      {...rowEnter(index)}
      data-workflow={workflow.id}
      className={cn(
        "group relative h-10 px-4 transition-colors duration-100 hover:bg-hover md:px-5",
        GRID,
        selected && "bg-accent-wash hover:bg-accent-wash"
      )}
    >
      <Checkbox
        checked={selected}
        onCheckedChange={(value) => onSelect(value === true)}
        aria-label={t("delete.selectWorkflow", { name: workflow.name })}
        className={cn(
          "relative z-10 transition-opacity duration-100 pointer-fine:opacity-0 pointer-fine:focus-visible:opacity-100 pointer-fine:group-hover:opacity-100",
          (selected || selecting) && "pointer-fine:opacity-100"
        )}
      />
      <StatusGlyph status={live ? "live" : "draft"} label={t(`status.${workflow.status}`)} />
      <Link
        href={`/workflows/${workflow.id}/edit`}
        data-row
        className="flex min-w-0 items-baseline gap-2 outline-none after:absolute after:inset-0 focus-visible:after:bg-selected"
      >
        <span className="relative truncate text-[13px] font-medium text-ink">{workflow.name}</span>
        <span className="relative hidden truncate text-xs text-ink-4 lg:inline">
          {t(`status.${workflow.status}`)}
        </span>
      </Link>
      <span className="relative hidden min-w-0 items-center gap-1 overflow-hidden md:flex">
        {workflow.documents.slice(0, 3).map((doc, i) => (
          <DocChip key={doc.id} index={i} variant="chip">
            {doc.documentType || `${t("builder.docSource.unnamedDoc")} ${i + 1}`}
          </DocChip>
        ))}
        {workflow.documents.length > 3 ? (
          <span className="text-xs text-ink-4">+{workflow.documents.length - 3}</span>
        ) : null}
      </span>
      <span className="relative hidden items-center gap-2 md:flex">
        {workflow.totalRuns ? (
          <>
            <span className="h-1 flex-1 overflow-hidden rounded-full bg-fail-wash">
              <motion.span
                className="block h-full rounded-full bg-pass"
                initial={{ width: 0 }}
                animate={{ width: `${workflow.successRate * 100}%` }}
                transition={{ duration: 0.5, ease: EASE_OUT, delay: index * 0.02 }}
              />
            </span>
            <span className="w-16 text-end text-xs tabular-nums text-ink-3">
              {format.number(workflow.totalRuns)} · {Math.round(workflow.successRate * 100)}%
            </span>
          </>
        ) : (
          <span className="text-xs text-ink-4">{t("row.neverRun")}</span>
        )}
      </span>
      <span className="relative text-end text-xs tabular-nums text-ink-3">
        {workflow.lastRun ? <When value={workflow.lastRun} /> : "—"}
      </span>
    </motion.li>
  );
}

/** Every workflow, newest first; select some (hover or X) to archive them together. */
export function WorkflowsList() {
  const t = useTranslations("workflows");
  const tCommon = useTranslations("common");
  const queryClient = useQueryClient();
  const listRef = useRef<HTMLUListElement>(null);
  useListKeys(listRef);
  const { workflows } = $api.useSuspenseQuery("get", "/v1/workflows").data;
  const canCreate = useCan("workflow:write");
  const [selection, setSelection] = useState<Set<string>>(new Set());
  const toggle = (id: string, on: boolean) =>
    setSelection((current) => {
      const next = new Set(current);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  useShortcut(
    "x",
    () => {
      const id = (document.activeElement?.closest("[data-workflow]") as HTMLElement | null)?.dataset
        .workflow;
      if (id) toggle(id, !selection.has(id));
    },
    { description: t("delete.selectAll") }
  );
  useShortcut("escape", () => setSelection(new Set()), {
    when: () => selection.size > 0,
    description: tCommon("cancel"),
  });

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
      <div className="flex flex-col items-center gap-2 px-6 py-24 text-center">
        <p className="text-[13px] font-medium text-ink">{t("emptyTitle")}</p>
        <p className="max-w-sm text-[13px] text-ink-3">{t("emptyHint")}</p>
        {canCreate ? (
          <Button className="mt-2" variant="primary" render={<Link href="/workflows/new" />}>
            {tCommon("newWorkflow")}
            <Kbd className="ms-1">C</Kbd>
          </Button>
        ) : null}
      </div>
    );
  }

  const selected = workflows.filter((w) => selection.has(w.id));
  const all = selection.size === workflows.length;
  const archive = async () => {
    const yes = await confirmAction({
      title: t("delete.confirmTitle", { count: selected.length }),
      description:
        selected.length <= 3
          ? t("delete.confirmDescriptionNamed", { names: selected.map((w) => w.name).join(", ") })
          : t("delete.confirmDescription", { count: selected.length }),
      confirmLabel: t("delete.confirmButton"),
      cancelLabel: tCommon("cancel"),
      danger: true,
    });
    if (yes) remove.mutate({ body: { ids: selected.map((w) => w.id) } });
  };

  return (
    <div className="flex min-h-[calc(100dvh-3.5rem)] flex-col">
      <div
        className={cn(
          "sticky top-[41px] z-10 h-8 border-b border-line bg-raised/95 px-4 text-xs text-ink-3 backdrop-blur-sm md:px-5",
          GRID
        )}
      >
        <Checkbox
          checked={all ? true : selection.size ? "indeterminate" : false}
          onCheckedChange={(value) =>
            setSelection(value === true ? new Set(workflows.map((w) => w.id)) : new Set())
          }
          aria-label={t("delete.selectAll")}
        />
        <span />
        <span>{t("columns.name")}</span>
        <span className="hidden md:block">{t("columns.documents")}</span>
        <span className="hidden md:block">{t("columns.passRate")}</span>
        <span className="text-end">{t("columns.lastRun")}</span>
      </div>
      <ul ref={listRef} className="flex-1 divide-y divide-line">
        {workflows.map((workflow, index) => (
          <WorkflowRow
            key={workflow.id}
            workflow={workflow}
            index={index}
            selected={selection.has(workflow.id)}
            selecting={selection.size > 0}
            onSelect={(on) => toggle(workflow.id, on)}
          />
        ))}
      </ul>
      <div className="sticky bottom-0 flex h-9 items-center gap-3 border-t border-line bg-panel/90 px-4 text-xs text-ink-3 backdrop-blur-md md:px-5">
        <span className="tabular-nums">{t("count", { count: workflows.length })}</span>
        <ListKeysHint
          extra={
            <span className="flex items-center gap-1">
              <Kbd>X</Kbd>
              {t("delete.select")}
            </span>
          }
        />
      </div>

      <AnimatePresence>
        {selection.size ? (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, transition: { duration: 0.12 } }}
            transition={{ type: "spring", duration: 0.28, bounce: 0 }}
            className="fixed inset-x-0 bottom-6 z-30 mx-auto flex w-fit items-center gap-1 rounded-lg bg-overlay p-1 ps-3 shadow-pop"
          >
            <span className="me-2 text-[13px] tabular-nums text-ink-2">
              {t("delete.selected", { count: selection.size })}
            </span>
            <Gate permission="workflow:delete">
              <Button
                variant="ghost"
                className="text-fail-ink hover:text-fail-ink"
                disabled={remove.isPending}
                onClick={archive}
              >
                <Archive />
                {t("delete.deleteSelected")}
              </Button>
            </Gate>
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
    </div>
  );
}
