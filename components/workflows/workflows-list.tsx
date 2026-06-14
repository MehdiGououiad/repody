"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import {
  Activity,
  ChevronRight,
  FileEdit,
  Pause,
  Play,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { browserApi } from "@/lib/api/openapi-client";
import type { Workflow } from "@/lib/types";
import { cn, formatNumber, formatPercent } from "@/lib/utils";

const statusConfig = {
  active: { variant: "success" as const, Icon: Play, key: "active" as const },
  paused: { variant: "warning" as const, Icon: Pause, key: "paused" as const },
  draft: { variant: "outline" as const, Icon: FileEdit, key: "draft" as const },
};

function WorkflowCheckbox({
  checked,
  onChange,
  ariaLabel,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  ariaLabel: string;
}) {
  return (
    <label
      className="inline-flex items-center justify-center shrink-0 cursor-pointer"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={ariaLabel}
        className="size-4 rounded border-border text-primary focus:ring-primary/30 cursor-pointer accent-primary"
      />
    </label>
  );
}

export function WorkflowsList({ initialWorkflows }: { initialWorkflows: Workflow[] }) {
  const t = useTranslations("workflows");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const router = useRouter();

  const [workflows, setWorkflows] = useState(initialWorkflows);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const allSelected = workflows.length > 0 && selected.size === workflows.length;
  const someSelected = selected.size > 0;

  const toggleAll = () => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(workflows.map((w) => w.id)));
    }
  };

  const toggleOne = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const selectedNames = useMemo(
    () => workflows.filter((w) => selected.has(w.id)).map((w) => w.name),
    [workflows, selected]
  );

  const handleDelete = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    setDeleting(true);
    try {
      const { error, response } = await browserApi.POST("/v1/workflows/bulk-delete", {
        body: { ids },
      });
      if (error || !response.ok) {
        throw new Error(`Delete failed: HTTP ${response.status}`);
      }
      setWorkflows((prev) => prev.filter((w) => !selected.has(w.id)));
      setSelected(new Set());
      toast.success(t("delete.success", { count: ids.length }));
      router.refresh();
    } catch {
      toast.error(tCommon("saveFailed"));
    } finally {
      setDeleting(false);
    }
  };

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
            checked={allSelected}
            ref={(el) => {
              if (el) el.indeterminate = someSelected && !allSelected;
            }}
            onChange={toggleAll}
            aria-label={t("delete.selectAll")}
            className="size-4 rounded border-border accent-primary cursor-pointer"
          />
          {t("delete.selectAll")}
        </label>
        {someSelected && (
          <>
            <span className="text-xs text-on-surface-variant">
              {t("delete.selected", { count: selected.size })}
            </span>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={deleting}
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t("delete.deleteSelected")}
            </Button>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workflows.map((w) => {
          const cfg = statusConfig[w.status as keyof typeof statusConfig] ?? statusConfig.draft;
          const isSelected = selected.has(w.id);
          return (
            <div
              key={w.id}
              className={cn(
                "panel-elevated rounded-xl p-5 transition-[border-color,box-shadow] duration-200 group flex flex-col gap-3 relative",
                isSelected ? "border-accent-blue ring-1 ring-accent-blue/25" : "hover:border-accent-blue/20"
              )}
            >
              <div className="flex items-start gap-3">
                <WorkflowCheckbox
                  checked={isSelected}
                  onChange={(checked) => toggleOne(w.id, checked)}
                  ariaLabel={t("delete.selectWorkflow", { name: w.name })}
                />
                <Link href={`/workflows/${w.id}/edit`} className="flex-1 min-w-0 flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold text-on-surface group-hover:text-primary transition-colors truncate">
                        {w.name}
                      </h3>
                      <p className="text-xs text-on-surface-variant mt-1 line-clamp-2">
                        {w.description}
                      </p>
                    </div>
                    <Badge variant={cfg.variant} className="shrink-0">
                      <cfg.Icon className="h-3 w-3" />
                      {t(`status.${cfg.key}`)}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-3 pt-3 border-t border-border text-center">
                    <div>
                      <div className="text-xs text-on-surface-variant uppercase tracking-wider">
                        {t("card.lastRun")}
                      </div>
                      <div className="text-sm font-medium mt-0.5 truncate">{w.lastRun ?? "—"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-on-surface-variant uppercase tracking-wider">
                        {t("card.success")}
                      </div>
                      <div
                        className={cn(
                          "text-sm font-semibold mt-0.5 inline-flex items-center gap-0.5 justify-center",
                          w.successRate > 0.95
                            ? "text-success"
                            : w.successRate > 0
                              ? "text-warning-strong"
                              : "text-on-surface-variant"
                        )}
                      >
                        {w.successRate > 0 ? (
                          <>
                            <TrendingUp className="h-3 w-3" />
                            {formatPercent(w.successRate, 1, locale)}
                          </>
                        ) : (
                          "—"
                        )}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-on-surface-variant uppercase tracking-wider">
                        {t("card.runs")}
                      </div>
                      <div className="text-sm font-medium mt-0.5 inline-flex items-center gap-0.5 justify-center">
                        <Activity className="h-3 w-3 text-on-surface-variant" />
                        {formatNumber(w.totalRuns, locale)}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-on-surface-variant">
                      {tCommon("owner")}: {w.owner}
                    </span>
                    <span className="inline-flex items-center gap-1 text-primary opacity-0 group-hover:opacity-100 transition-opacity font-medium">
                      {tCommon("open")}
                      <ChevronRight className="h-3 w-3" />
                    </span>
                  </div>
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={handleDelete}
        title={t("delete.confirmTitle", { count: selected.size })}
        description={
          selectedNames.length <= 3
            ? t("delete.confirmDescriptionNamed", { names: selectedNames.join(", ") })
            : t("delete.confirmDescription", { count: selected.size })
        }
        confirmLabel={t("delete.confirmButton")}
      />
    </>
  );
}
