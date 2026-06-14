"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Code,
  Brain,
  Plus,
  Trash2,
  AlertOctagon,
  AlertTriangle,
  Sparkles,
  FileText,
  GitCompare,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConditionBuilder } from "./condition-builder";
import { conditionsToExpression } from "@/lib/rules/expression";
import { resolveDocumentFields } from "@/lib/rules/document-fields";
import { useRulesLibraryCatalog } from "@/lib/hooks/use-catalog-queries";
import { getRuleIssues } from "@/lib/rules/rule-validation";
import { cn, shortId } from "@/lib/utils";
import { SectionHeading } from "@/components/layout/section-heading";
import type {
  ConditionJunction,
  DocumentDef,
  RuleCondition,
  RuleKind,
  RuleScope,
  RuleSeverity,
  RuleTemplate,
  WorkflowRule,
} from "@/lib/types";

function LlmPromptEditor({
  value,
  fields,
  onChange,
}: {
  value: string;
  fields: { label: string; token: string }[];
  onChange: (value: string) => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const insertField = (token: string) => {
    const textarea = textareaRef.current;
    const reference = `@${token}`;
    if (!textarea) {
      onChange(`${value}${value ? " " : ""}${reference}`);
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const needsSpace = start > 0 && !/\s/.test(value[start - 1] ?? "");
    const insertion = `${needsSpace ? " " : ""}${reference}`;
    onChange(`${value.slice(0, start)}${insertion}${value.slice(end)}`);
    requestAnimationFrame(() => {
      const cursor = start + insertion.length;
      textarea.focus();
      textarea.setSelectionRange(cursor, cursor);
    });
  };

  return (
    <div className="space-y-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("llmPromptPlaceholder")}
        aria-label={t("promptLabel")}
        rows={4}
        className="w-full rounded-lg border border-input bg-surface-container-low px-3 py-2 font-mono text-[12px] text-on-surface focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
      />
      <div className="rounded-lg border border-border/70 bg-surface-container-lowest px-3 py-2">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
          {t("availableFields")}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {fields.length ? fields.map((field) => (
            <button
              key={field.token}
              type="button"
              onClick={() => insertField(field.token)}
              className="rounded-md border border-accent-blue/30 bg-accent-blue/5 px-2 py-1 font-mono text-[11px] text-accent-blue transition-colors hover:bg-accent-blue/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              title={field.label}
            >
              @{field.token}
            </button>
          )) : (
            <span className="text-[11px] text-on-surface-variant">{t("noFieldsForPrompt")}</span>
          )}
        </div>
        <p className="mt-2 text-[11px] text-on-surface-variant">
          {t("fieldReferenceHint")}
        </p>
      </div>
    </div>
  );
}

// ── Kind toggle ───────────────────────────────────────────────────────────────

function KindToggle({ kind, onChange }: { kind: RuleKind; onChange: (k: RuleKind) => void }) {
  const t = useTranslations("workflows.builder.rules");
  return (
    <div className="flex rounded-lg border border-border overflow-hidden w-fit text-[11px] font-medium">
      <button
        type="button"
        aria-pressed={kind === "logic"}
        onClick={() => onChange("logic")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          kind === "logic"
            ? "bg-primary text-primary-foreground"
            : "bg-surface-container-low text-on-surface-variant hover:bg-surface-bright"
        )}
      >
        <Code className="h-3 w-3" />
        {t("kindLogic")}
      </button>
      <div className="w-px bg-border" />
      <button
        type="button"
        aria-pressed={kind === "llm"}
        onClick={() => onChange("llm")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          kind === "llm"
            ? "bg-accent-blue text-white"
            : "bg-surface-container-low text-on-surface-variant hover:bg-surface-bright"
        )}
      >
        <Brain className="h-3 w-3" />
        {t("kindLlm")}
      </button>
    </div>
  );
}

// ── Scope toggle ──────────────────────────────────────────────────────────────

function ScopeToggle({
  scope,
  onChange,
  canCross,
}: {
  scope: RuleScope;
  onChange: (s: RuleScope) => void;
  canCross: boolean;
}) {
  const t = useTranslations("workflows.builder.rules");
  return (
    <div className="flex rounded-lg border border-border overflow-hidden w-fit text-[11px] font-medium">
      <button
        type="button"
        aria-pressed={scope === "intra"}
        onClick={() => onChange("intra")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          scope === "intra"
            ? "bg-primary text-primary-foreground"
            : "bg-surface-container-low text-on-surface-variant hover:bg-surface-bright"
        )}
      >
        <FileText className="h-3 w-3" />
        {t("scopeIntraShort")}
      </button>
      <div className="w-px bg-border" />
      <button
        type="button"
        aria-pressed={scope === "cross"}
        aria-disabled={!canCross}
        onClick={() => canCross && onChange("cross")}
        title={!canCross ? t("crossRequiresTwoDocs") : undefined}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          scope === "cross"
            ? "bg-primary text-primary-foreground"
            : "bg-surface-container-low text-on-surface-variant",
          canCross ? "hover:bg-surface-bright" : "opacity-40 cursor-not-allowed"
        )}
      >
        <GitCompare className="h-3 w-3" />
        {t("scopeCrossShort")}
      </button>
    </div>
  );
}

// ── Rule card ─────────────────────────────────────────────────────────────────

function RuleCard({
  rule,
  documents,
  onChange,
  onRemove,
}: {
  rule: WorkflowRule;
  documents: DocumentDef[];
  onChange: (patch: Partial<WorkflowRule>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const tCommon = useTranslations("common");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const isLlm = rule.kind === "llm";
  const isCross = rule.scope === "cross";
  const canCross = documents.length >= 2;
  const fields = resolveDocumentFields(documents, rule.appliesTo);

  const conditions: RuleCondition[] = rule.conditions ?? [
    { id: "c0", left: { kind: "field", value: "" }, operator: "==", right: { kind: "literal", value: "" } },
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

  const handleJunctionChange = (j: ConditionJunction) => {
    onChange({
      conditionJunction: j,
      body: conditionsToExpression(conditions, j),
    });
  };

  const ruleIssues = getRuleIssues(
    rule,
    isLlm ? fields.map((field) => field.token) : undefined
  );

  return (
    <div
      className={cn(
        "panel-elevated rounded-xl p-4 group space-y-4",
        isLlm ? "border-l-4 border-l-accent-blue border-border" : "border-border"
      )}
    >
      {/* ① Name + delete */}
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

      {/* ② Scope + Kind toggles */}
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
          <KindToggle kind={rule.kind} onChange={(k) => onChange({ kind: k })} />
        </div>
      </div>

      {/* ③ Document selector */}
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

      {/* ④ Rule body — structured for logic, free-text for LLM */}
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
            junction={junction}
            fields={fields}
            onConditionsChange={handleConditionsChange}
            onJunctionChange={handleJunctionChange}
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

      {/* ⑤ Severity */}
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

// ── Rules panel ───────────────────────────────────────────────────────────────

export function RulesPanel({
  rules,
  documents,
  onChange,
  onEnableLlmValidation,
  initialRuleLibrary,
}: {
  rules: WorkflowRule[];
  documents: DocumentDef[];
  onChange: (rules: WorkflowRule[]) => void;
  onEnableLlmValidation: () => void;
  initialRuleLibrary?: RuleTemplate[];
}) {
  const t = useTranslations("workflows.builder.rules");
  const shouldFetchLibrary = initialRuleLibrary === undefined;
  const { data: fetchedLibrary = [] } = useRulesLibraryCatalog(shouldFetchLibrary);
  const ruleLibrary = initialRuleLibrary ?? fetchedLibrary;

  const updateRule = (id: string, patch: Partial<WorkflowRule>) => {
    if (patch.kind === "llm") onEnableLlmValidation();
    onChange(rules.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const remove = (id: string) => onChange(rules.filter((r) => r.id !== id));

  const addBlank = () =>
    onChange([
      ...rules,
      {
        id: `r${shortId()}`,
        name: "",
        kind: "logic",
        scope: "intra",
        appliesTo: documents[0] ? [documents[0].id] : [],
        conditions: [{ id: "c0", left: { kind: "field", value: "" }, operator: "==" as const, right: { kind: "literal", value: "" } }],
        conditionJunction: "AND" as ConditionJunction,
        body: "",
        severity: "flag",
      },
    ]);

  const addFromLibrary = (templateId: string) => {
    const tpl = ruleLibrary.find((x) => x.id === templateId);
    if (!tpl) return;
    if (tpl.kind === "llm") onEnableLlmValidation();
    const appliesTo =
      tpl.scope === "cross" && documents.length >= 2
        ? [documents[0].id, documents[1].id]
        : documents[0] ? [documents[0].id] : [];
    onChange([
      ...rules,
      {
        id: `r${shortId()}`,
        name: tpl.name,
        kind: tpl.kind,
        scope: tpl.scope,
        appliesTo,
        body: tpl.body,
        severity: tpl.severity,
      },
    ]);
  };

  const intraCount = rules.filter((r) => r.scope === "intra").length;
  const crossCount = rules.filter((r) => r.scope === "cross").length;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <SectionHeading title={t("title")} description={t("hint")} eyebrow="Validation" />
        <p className="text-xs text-on-surface-variant/90 rounded-lg border border-border/70 bg-surface-container-low/80 px-3 py-2">
          {t("runsOnOcr")}
        </p>
      </div>

      <Tabs defaultValue="active" className="w-full">
        <div className="flex items-center justify-between mb-3">
          <TabsList className="w-fit">
            <TabsTrigger value="active">{t("active")} ({rules.length})</TabsTrigger>
            <TabsTrigger value="library">{t("library")}</TabsTrigger>
          </TabsList>
          <Badge variant="secondary" className="text-[10px]">
            {intraCount} {t("scopeIntraShort")} · {crossCount} {t("scopeCrossShort")}
          </Badge>
        </div>

        {/* Active rules */}
        <TabsContent value="active" className="space-y-3 mt-0">
          {rules.length === 0 ? (
            <div className="border-2 border-dashed border-outline-variant rounded-xl py-12 text-center text-sm text-on-surface-variant">
              {t("emptyActive")}
            </div>
          ) : (
            rules.map((r) => (
              <RuleCard
                key={r.id}
                rule={r}
                documents={documents}
                onChange={(patch) => updateRule(r.id, patch)}
                onRemove={() => remove(r.id)}
              />
            ))
          )}
          <Button variant="outline" size="sm" onClick={addBlank} className="w-full">
            <Plus className="h-3.5 w-3.5" />
            {t("addRule")}
          </Button>
        </TabsContent>

        {/* Library */}
        <TabsContent value="library" className="space-y-4 mt-0">
          {(["intra", "cross"] as RuleScope[]).map((scope) => {
            const isIntra = scope === "intra";
            const ScopeIcon = isIntra ? FileText : GitCompare;
            const scopeLabel = isIntra ? t("scopeIntra") : t("scopeCross");
            const templates = ruleLibrary.filter((tpl) => tpl.scope === scope);
            return (
              <div key={scope} className="space-y-2">
                <div className="flex items-center gap-2">
                  <ScopeIcon className="h-3.5 w-3.5 text-on-surface-variant" />
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    {scopeLabel}
                  </span>
                </div>
                {templates.map((tpl) => {
                  const isLlm = tpl.kind === "llm";
                  const Icon = isLlm ? Brain : Code;
                  const added = rules.some((r) => r.name === tpl.name);
                  const disabled = added || (scope === "cross" && documents.length < 2);
                  return (
                    <div
                      key={tpl.id}
                      className={cn(
                        "border rounded-lg p-3 hover:border-outline-variant transition-colors",
                        isLlm ? "border-l-4 border-l-accent-blue border-border" : "border-border"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className={cn("h-3.5 w-3.5 shrink-0", isLlm ? "text-accent-blue" : "text-on-surface-variant")} />
                        <span className="text-sm font-semibold">{tpl.name}</span>
                        <Badge variant={isLlm ? "info" : "secondary"} className="text-[9px] gap-0.5">
                          {isLlm ? <Sparkles className="h-2.5 w-2.5" /> : null}
                          {isLlm ? t("kindLlm") : t("kindLogic")}
                        </Badge>
                      </div>
                      <p className="text-xs text-on-surface-variant mb-2">{tpl.description}</p>
                      <div className="flex items-center justify-between gap-2">
                        <code className={cn("text-[10px] truncate flex-1 font-mono text-on-surface-variant")}>
                          {tpl.body}
                        </code>
                        <Button
                          size="sm"
                          variant={added ? "outline" : "default"}
                          className="h-7 shrink-0"
                          disabled={disabled}
                          title={scope === "cross" && documents.length < 2 ? t("crossRequiresTwoDocs") : undefined}
                          onClick={() => addFromLibrary(tpl.id)}
                        >
                          {added ? t("added") : <><Plus className="h-3 w-3" />{t("addRule")}</>}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </TabsContent>
      </Tabs>
    </div>
  );
}
