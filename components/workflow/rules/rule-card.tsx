"use client";

import { AlertOctagon, AlertTriangle, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCatalog } from "@/lib/hooks/use-catalog";
import { fieldOptions, tableOptions } from "@/lib/rules/document-fields";
import type { DocumentDef, RuleCheck, RuleScope, RuleSeverity, WorkflowRule } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ConditionBuilder } from "./condition-builder";
import { ScopeToggle } from "./scope-toggle";

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
  const canCross = documents.length >= 2;
  const catalog = useCatalog();
  const fields = fieldOptions(documents, rule.appliesTo);
  const tables = catalog ? tableOptions(documents, rule.appliesTo, catalog) : [];

  const switchScope = (s: RuleScope) => {
    if (s === "intra") {
      onChange({ scope: "intra", appliesTo: rule.appliesTo.slice(0, 1) });
    } else {
      const next =
        rule.appliesTo.length >= 2
          ? rule.appliesTo.slice(0, 2)
          : [
              rule.appliesTo[0] ?? documents[0]?.id ?? "",
              documents.find((d) => !rule.appliesTo.includes(d.id))?.id ?? "",
            ].filter(Boolean);
      onChange({ scope: "cross", appliesTo: next });
    }
  };

  const toggleDoc = (docId: string) => {
    if (isCross) {
      if (rule.appliesTo.includes(docId)) return;
      const slot =
        rule.appliesTo.length >= 2 ? [rule.appliesTo[0], docId] : [...rule.appliesTo, docId];
      onChange({ appliesTo: slot.slice(0, 2) });
    } else {
      onChange({ appliesTo: [docId] });
    }
  };

  const ruleIssues = validation?.issues ?? [];

  return (
    <div className="rounded-xl p-4 group space-y-4 border-line">
      <div className="flex items-center gap-2">
        <Input
          value={rule.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder={t("ruleName")}
          aria-label={t("ruleName")}
          className="h-8 text-sm font-semibold border-transparent bg-transparent shadow-none focus-visible:bg-panel focus-visible:border-line-strong px-2 -ml-2"
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 opacity-0 group-hover:opacity-100 shrink-0"
          onClick={() => setConfirmOpen(true)}
          aria-label={tCommon("delete")}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          onConfirm={onRemove}
          title={tCommon("confirmDelete")}
          description={`${rule.name || t("newLogicName")} — ${tCommon("deleteWarning")}`}
        />
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1">
          <p className="text-2xs font-semibold text-ink-3">{t("appliesTo")}</p>
          <ScopeToggle scope={rule.scope} onChange={switchScope} canCross={canCross} />
        </div>
      </div>

      <div className="space-y-1.5">
        <p className="text-2xs font-semibold text-ink-3">
          {isCross ? t("selectTwoDocs") : t("selectOneDoc")}
        </p>
        {documents.length === 0 ? (
          <p className="text-2xs text-ink-3 italic">{t("noDocsYet")}</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {documents.map((doc, idx) => {
              const pos = rule.appliesTo.indexOf(doc.id);
              const isSelected = pos !== -1;
              return (
                <button
                  type="button"
                  key={doc.id}
                  aria-pressed={isSelected}
                  onClick={() => toggleDoc(doc.id)}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-2xs font-medium transition-colors",
                    isSelected
                      ? "bg-accent text-on-accent border-accent"
                      : "bg-transparent text-ink-3 border-line hover:border-line-strong"
                  )}
                >
                  {isCross && isSelected && (
                    <span className="text-2xs opacity-70">{pos === 0 ? "A" : "B"}</span>
                  )}
                  {doc.documentType || `${t("unnamedDoc")} ${idx + 1}`}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        <p className="text-2xs font-semibold text-ink-3">{t("expressionLabel")}</p>

        <ConditionBuilder
          conditions={rule.conditions}
          fields={fields}
          tables={tables}
          checks={validation?.checks ?? []}
          onConditionsChange={(conditions) => onChange({ conditions })}
        />
        {ruleIssues.length > 0 && (
          <ul className="text-2xs text-fail-ink space-y-0.5 rounded-lg border border-fail/30 bg-fail/5 px-3 py-2 list-disc pl-5">
            {ruleIssues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex items-center gap-3">
        <p className="text-2xs font-semibold text-ink-3 shrink-0">{t("onFail")}</p>
        <Select
          value={rule.severity}
          onValueChange={(v) => onChange({ severity: v as RuleSeverity })}
        >
          <SelectTrigger className="h-7 w-[160px] text-2xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="reject" className="text-xs">
              <span className="inline-flex items-center gap-1.5">
                <AlertOctagon className="h-3 w-3 text-fail-ink" />
                {t("severityReject")}
              </span>
            </SelectItem>
            <SelectItem value="flag" className="text-xs">
              <span className="inline-flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3 text-warn-ink" />
                {t("severityFlag")}
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
