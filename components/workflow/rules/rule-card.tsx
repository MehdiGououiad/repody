"use client";

import { MoreHorizontal, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { useCatalog } from "@/lib/hooks/use-catalog";
import { fieldOptions, tableOptions } from "@/lib/rules/document-fields";
import type { DocumentDef, RuleCheck, RuleScope, RuleSeverity, WorkflowRule } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ConditionBuilder } from "./condition-builder";
import { ScopeToggle } from "./scope-toggle";

const LABEL = "w-24 shrink-0 pt-1.5 text-xs text-ink-3";

/** One rule, read as a sentence: on these documents, when these conditions, if it fails. */
export function RuleCard({
  rule,
  documents,
  validation,
  onChange,
  onRemove,
}: {
  rule: WorkflowRule;
  documents: DocumentDef[];
  validation?: RuleCheck;
  onChange: (patch: Partial<WorkflowRule>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const tCommon = useTranslations("common");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const isCross = rule.scope === "cross";
  const catalog = useCatalog();
  const fields = fieldOptions(documents, rule.appliesTo);
  const tables = catalog ? tableOptions(documents, rule.appliesTo, catalog) : [];
  const issues = validation?.issues ?? [];

  const switchScope = (scope: RuleScope) => {
    if (scope === "intra") {
      onChange({ scope, appliesTo: rule.appliesTo.slice(0, 1) });
      return;
    }
    const next =
      rule.appliesTo.length >= 2
        ? rule.appliesTo.slice(0, 2)
        : [
            rule.appliesTo[0] ?? documents[0]?.id ?? "",
            documents.find((d) => !rule.appliesTo.includes(d.id))?.id ?? "",
          ].filter(Boolean);
    onChange({ scope, appliesTo: next });
  };
  const toggleDoc = (docId: string) => {
    if (!isCross) {
      onChange({ appliesTo: [docId] });
      return;
    }
    if (rule.appliesTo.includes(docId)) return;
    const slot =
      rule.appliesTo.length >= 2 ? [rule.appliesTo[0], docId] : [...rule.appliesTo, docId];
    onChange({ appliesTo: slot.slice(0, 2) });
  };

  return (
    <section className="overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]">
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={onRemove}
        title={t("removeTitle", { name: rule.name || t("newLogicName") })}
        description={tCommon("deleteWarning")}
        confirmLabel={tCommon("remove")}
      />
      <header className="flex h-11 items-center gap-2 border-b border-line bg-raised px-3">
        <StatusGlyph
          status={issues.length ? "warning" : "passed"}
          label={issues.length ? t("hasIssues") : t("valid")}
        />
        <input
          value={rule.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder={t("ruleName")}
          aria-label={t("ruleName")}
          className="h-7 min-w-0 flex-1 rounded-md bg-transparent px-1.5 text-sm font-medium text-ink outline-none transition-colors duration-100 placeholder:text-ink-4 hover:bg-hover focus-visible:bg-field focus-visible:shadow-[inset_0_0_0_1px_var(--accent)] focus-visible:outline-none"
        />
        <ScopeToggle scope={rule.scope} onChange={switchScope} canCross={documents.length >= 2} />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={t("ruleActions")}>
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onSelect={() => setConfirmOpen(true)}
              className="text-fail-ink focus:text-fail-ink [&_svg]:text-fail-ink"
            >
              <Trash2 />
              {t("removeRule")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <div className="flex flex-col gap-4 p-4">
        <div className="flex gap-3">
          <span className={LABEL}>{isCross ? t("selectTwoDocs") : t("selectOneDoc")}</span>
          {documents.length === 0 ? (
            <p className="pt-1.5 text-sm text-ink-3">{t("noDocsYet")}</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              {documents.map((doc, idx) => {
                const pos = rule.appliesTo.indexOf(doc.id);
                const selected = pos !== -1;
                return (
                  <button
                    type="button"
                    key={doc.id}
                    aria-pressed={selected}
                    onClick={() => toggleDoc(doc.id)}
                    className={cn(
                      "flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2 text-sm transition-colors duration-100",
                      selected
                        ? "bg-accent-wash text-accent-ink"
                        : "text-ink-3 shadow-[inset_0_0_0_1px_var(--line-strong)] hover:text-ink"
                    )}
                  >
                    {isCross && selected ? (
                      <span className="text-xs font-semibold">{pos === 0 ? "A" : "B"}</span>
                    ) : null}
                    {doc.documentType || `${t("unnamedDoc")} ${idx + 1}`}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <span className={LABEL}>{t("expressionLabel")}</span>
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <ConditionBuilder
              conditions={rule.conditions}
              fields={fields}
              tables={tables}
              checks={validation?.checks ?? []}
              onConditionsChange={(conditions) => onChange({ conditions })}
            />
            {issues.length ? (
              <ul className="flex flex-col gap-0.5 text-xs text-warn-ink">
                {issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={cn(LABEL, "pt-0")}>{t("onFail")}</span>
          <Select
            value={rule.severity}
            onValueChange={(v) => onChange({ severity: v as RuleSeverity })}
          >
            <SelectTrigger className="w-auto min-w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="reject">
                <span className="flex items-center gap-2">
                  <StatusGlyph status="failed" />
                  {t("severityReject")}
                </span>
              </SelectItem>
              <SelectItem value="flag">
                <span className="flex items-center gap-2">
                  <StatusGlyph status="warning" />
                  {t("severityFlag")}
                </span>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </section>
  );
}
