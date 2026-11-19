"use client";

import { Toggle } from "@ui-sdk/react/toggle";
import { MoreHorizontal, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { BareInput } from "@/components/ui/input";
import { Menu, MenuContent, MenuItem, MenuTrigger } from "@/components/ui/menu";
import { confirmAction } from "@/components/ui/overlays";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { catalog } from "@/lib/catalog";
import { docColor } from "@/lib/doc-color";
import { fieldOptions, tableOptions } from "@/lib/rules/document-fields";
import type {
  DocumentDef,
  RuleCheck,
  RuleScope,
  RuleSeverity,
  RunAuditRule,
  WorkflowRule,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { ConditionBuilder } from "./condition-builder";
import { ScopeToggle } from "./scope-toggle";

const LABEL = "w-24 shrink-0 pt-1.5 text-xs text-ink-3";

export function RuleCard({
  rule,
  documents,
  validation,
  result,
  onSwitchFieldToNumber,
  onChange,
  onRemove,
}: {
  rule: WorkflowRule;
  documents: DocumentDef[];
  validation?: RuleCheck;
  result?: RunAuditRule;
  onSwitchFieldToNumber?: (fieldName: string) => void;
  onChange: (patch: Partial<WorkflowRule>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const tCommon = useTranslations("common");
  const isCross = rule.scope === "cross";
  const fields = fieldOptions(documents, rule.appliesTo);
  const tables = tableOptions(documents, rule.appliesTo, catalog);
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
    <section className="overflow-hidden rounded-lg bg-panel shadow-[0_0_0_1px_var(--line)]">
      <header className="flex h-10 items-center gap-2 border-b border-line bg-raised px-3">
        <StatusGlyph
          status={issues.length ? "warning" : "passed"}
          label={issues.length ? t("hasIssues") : t("valid")}
        />
        <BareInput
          value={rule.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder={t("ruleName")}
          aria-label={t("ruleName")}
          className="h-7 min-w-0 flex-1 rounded-md bg-transparent px-1.5 text-[13px] font-semibold text-ink outline-none transition-colors duration-100 placeholder:text-ink-4 hover:bg-hover focus-visible:bg-field focus-visible:shadow-[inset_0_0_0_1px_var(--accent)] focus-visible:outline-none"
        />
        {result ? (
          <span
            title={result.detail || undefined}
            className={cn(
              "inline-flex h-5 shrink-0 items-center gap-1.5 rounded-full px-2 text-xs font-medium",
              result.status === "passed" && "bg-pass-wash text-pass-ink",
              result.status === "failed" && "bg-fail-wash text-fail-ink",
              result.status === "skipped" && "bg-selected text-ink-3"
            )}
          >
            <StatusGlyph
              status={result.status === "skipped" ? "waiting" : result.status}
              className="size-3"
            />
            {t(`onSample.${result.status}`)}
          </span>
        ) : null}
        <ScopeToggle scope={rule.scope} onChange={switchScope} canCross={documents.length >= 2} />
        <Menu
          onAction={async () => {
            const yes = await confirmAction({
              title: t("removeTitle", { name: rule.name || t("newLogicName") }),
              description: tCommon("deleteWarning"),
              confirmLabel: tCommon("remove"),
              cancelLabel: tCommon("cancel"),
              danger: true,
            });
            if (yes) onRemove();
          }}
        >
          <MenuTrigger
            render={
              <Button variant="ghost" size="icon-sm" aria-label={t("ruleActions")}>
                <MoreHorizontal />
              </Button>
            }
          />
          <MenuContent align="end">
            <MenuItem value="remove" danger>
              <Trash2 />
              {t("removeRule")}
            </MenuItem>
          </MenuContent>
        </Menu>
      </header>

      <div className="flex flex-col gap-3 p-3.5">
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
                  <Toggle
                    key={doc.id}
                    pressed={selected}
                    onPressedChange={() => toggleDoc(doc.id)}
                    className={cn(
                      "flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2 text-[13px] transition-colors duration-100",
                      selected
                        ? cn(docColor(idx).wash, docColor(idx).ink, "font-medium")
                        : "text-ink-3 shadow-[inset_0_0_0_1px_var(--line-strong)] hover:text-ink"
                    )}
                  >
                    <span className={cn("size-1.5 rounded-full", docColor(idx).dot)} aria-hidden />
                    {isCross && selected ? (
                      <span className="text-xs font-semibold">{pos === 0 ? "A" : "B"}</span>
                    ) : null}
                    {doc.documentType || `${t("unnamedDoc")} ${idx + 1}`}
                  </Toggle>
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
              onSwitchFieldToNumber={onSwitchFieldToNumber}
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
            onValueChange={(v: string | null) =>
              v !== null && onChange({ severity: v as RuleSeverity })
            }
          >
            <SelectTrigger className="w-auto min-w-44" aria-label={t("onFail")}>
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
