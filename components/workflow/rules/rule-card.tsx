"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AlertOctagon, AlertTriangle, Trash2 } from "lucide-react";
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
import { ConditionBuilder } from "../condition-builder";
import { conditionsToExpression } from "@/lib/rules/expression";
import { resolveDocumentFields, resolveTableFields } from "@/lib/rules/document-fields";
import { cn } from "@/lib/utils";
import type {
  ConditionJunction,
  DocumentDef,
  RuleCondition,
  RuleScope,
  RuleSeverity,
  WorkflowRule,
} from "@/lib/types";
import { LlmPromptEditor } from "./llm-prompt-editor";
import { KindToggle, ScopeToggle } from "./kind-scope-toggles";

export function RuleCard({
  rule,
  documents,
  issues,
  onChange,
  onRemove,
  llmValidationEnabled = false,
}: {
  rule: WorkflowRule;
  documents: DocumentDef[];
  issues?: string[];
  onChange: (patch: Partial<WorkflowRule>) => void;
  onRemove: () => void;
  llmValidationEnabled?: boolean;
}) {
  const t = useTranslations("workflows.builder.rules");
  const tCommon = useTranslations("common");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const isLlm = rule.kind === "llm";
  const isCross = rule.scope === "cross";
  const canCross = documents.length >= 2;
  const fields = resolveDocumentFields(documents, rule.appliesTo);
  const tableFields = resolveTableFields(documents, rule.appliesTo);

  const conditions: RuleCondition[] = rule.conditions ?? [
    {
      id: "c0",
      left: { kind: "field", value: "" },
      operator: "==",
      right: { kind: "literal", value: "" },
    },
  ];
  const junction: ConditionJunction = rule.conditionJunction ?? "AND";

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

  const handleConditionsChange = (next: RuleCondition[]) => {
    onChange({
      conditions: next,
      body: conditionsToExpression(next, junction),
    });
  };

  const ruleIssues = issues ?? [];

  return (
    <div
      className={cn(
        "panel-elevated rounded-xl p-4 group space-y-4",
        isLlm ? "border-l-4 border-l-accent-blue border-border" : "border-border"
      )}
    >
      <div className="flex items-center gap-2">
        <Input
          value={rule.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder={t("ruleName")}
          aria-label={t("ruleName")}
          className="h-8 text-sm font-semibold border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input px-2 -ml-2"
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
          <p className="text-[10px] uppercase tracking-wider font-semibold text-on-surface-variant">
            {t("appliesTo")}
          </p>
          <ScopeToggle scope={rule.scope} onChange={switchScope} canCross={canCross} />
        </div>
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wider font-semibold text-on-surface-variant">
            {t("checkType")}
          </p>
          <KindToggle
            kind={rule.kind}
            llmEnabled={llmValidationEnabled}
            onChange={(k) => onChange({ kind: k })}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <p className="text-[10px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {isCross ? t("selectTwoDocs") : t("selectOneDoc")}
        </p>
        {documents.length === 0 ? (
          <p className="text-[11px] text-on-surface-variant italic">{t("noDocsYet")}</p>
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
                    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium transition-colors",
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-transparent text-on-surface-variant border-border hover:border-outline"
                  )}
                >
                  {isCross && isSelected && (
                    <span className="text-[9px] opacity-70">{pos === 0 ? "A" : "B"}</span>
                  )}
                  {doc.documentType || `${t("unnamedDoc")} ${idx + 1}`}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        <p className="text-[10px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {isLlm ? t("promptLabel") : t("expressionLabel")}
        </p>

        {isLlm ? (
          <LlmPromptEditor
            value={rule.body}
            fields={fields}
            onChange={(body) => onChange({ body })}
          />
        ) : (
          <ConditionBuilder
            conditions={conditions}
            fields={fields}
            tableFields={tableFields}
            onConditionsChange={handleConditionsChange}
          />
        )}
        {ruleIssues.length > 0 && (
          <ul className="text-[11px] text-danger space-y-0.5 rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 list-disc pl-5">
            {ruleIssues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex items-center gap-3">
        <p className="text-[10px] uppercase tracking-wider font-semibold text-on-surface-variant shrink-0">
          {t("onFail")}
        </p>
        <Select
          value={rule.severity}
          onValueChange={(v) => onChange({ severity: v as RuleSeverity })}
        >
          <SelectTrigger className="h-7 w-[160px] text-[11px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="reject" className="text-xs">
              <span className="inline-flex items-center gap-1.5">
                <AlertOctagon className="h-3 w-3 text-danger" />
                {t("severityReject")}
              </span>
            </SelectItem>
            <SelectItem value="flag" className="text-xs">
              <span className="inline-flex items-center gap-1.5">
                <AlertTriangle className="h-3 w-3 text-warning-strong" />
                {t("severityFlag")}
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
