"use client";

import { useTranslations } from "next-intl";
import {
  Brain,
  Code,
  FileText,
  GitCompare,
  Plus,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRulesLibraryCatalog } from "@/lib/hooks/use-catalog-queries";
import { cn, shortId } from "@/lib/utils";
import { SectionHeading } from "@/components/layout/section-heading";
import type {
  ConditionJunction,
  DocumentDef,
  RuleScope,
  RuleTemplate,
  WorkflowRule,
} from "@/lib/types";
import { RuleCard } from "./rule-card";

export function RulesPanel({
  rules,
  documents,
  onChange,
  initialRuleLibrary,
}: {
  rules: WorkflowRule[];
  documents: DocumentDef[];
  onChange: (rules: WorkflowRule[]) => void;
  initialRuleLibrary?: RuleTemplate[];
}) {
  const t = useTranslations("workflows.builder.rules");
  const shouldFetchLibrary = initialRuleLibrary === undefined;
  const { data: fetchedLibrary = [] } = useRulesLibraryCatalog(shouldFetchLibrary);
  const ruleLibrary = initialRuleLibrary ?? fetchedLibrary;

  const updateRule = (id: string, patch: Partial<WorkflowRule>) => {
    onChange(rules.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const remove = (id: string) => onChange(rules.filter((r) => r.id !== id));

  const addRule = (kind: "logic" | "llm") =>
    onChange([
      ...rules,
      {
        id: `r${shortId()}`,
        name: "",
        kind,
        scope: "intra",
        appliesTo: documents[0] ? [documents[0].id] : [],
        conditions:
          kind === "logic"
            ? [
                {
                  id: "c0",
                  left: { kind: "field", value: "" },
                  operator: "==" as const,
                  right: { kind: "literal", value: "" },
                },
              ]
            : undefined,
        conditionJunction: kind === "logic" ? ("AND" as ConditionJunction) : undefined,
        body: "",
        severity: "flag",
      },
    ]);

  const addFromLibrary = (templateId: string) => {
    const tpl = ruleLibrary.find((x) => x.id === templateId);
    if (!tpl) return;
    const appliesTo =
      tpl.scope === "cross" && documents.length >= 2
        ? [documents[0].id, documents[1].id]
        : documents[0]
          ? [documents[0].id]
          : [];
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
            <TabsTrigger value="active">
              {t("active")} ({rules.length})
            </TabsTrigger>
            <TabsTrigger value="library">{t("library")}</TabsTrigger>
          </TabsList>
          <Badge variant="secondary" className="text-[10px]">
            {intraCount} {t("scopeIntraShort")} · {crossCount} {t("scopeCrossShort")}
          </Badge>
        </div>

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
          <div className="grid gap-2 sm:grid-cols-2">
            <Button variant="outline" size="sm" onClick={() => addRule("logic")} className="w-full">
              <Code className="h-3.5 w-3.5" />
              {t("addLogic")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => addRule("llm")}
              className="w-full border-accent-blue/30 hover:border-accent-blue/50 hover:bg-accent-blue/5"
            >
              <Brain className="h-3.5 w-3.5 text-accent-blue" />
              {t("addLlm")}
            </Button>
          </div>
        </TabsContent>

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
                        <Icon
                          className={cn(
                            "h-3.5 w-3.5 shrink-0",
                            isLlm ? "text-accent-blue" : "text-on-surface-variant"
                          )}
                        />
                        <span className="text-sm font-semibold">{tpl.name}</span>
                        <Badge variant={isLlm ? "info" : "secondary"} className="text-[9px] gap-0.5">
                          {isLlm ? <Sparkles className="h-2.5 w-2.5" /> : null}
                          {isLlm ? t("kindLlm") : t("kindLogic")}
                        </Badge>
                      </div>
                      <p className="text-xs text-on-surface-variant mb-2">{tpl.description}</p>
                      <div className="flex items-center justify-between gap-2">
                        <code className="text-[10px] truncate flex-1 font-mono text-on-surface-variant">
                          {tpl.body}
                        </code>
                        <Button
                          size="sm"
                          variant={added ? "outline" : "default"}
                          className="h-7 shrink-0"
                          disabled={disabled}
                          title={
                            scope === "cross" && documents.length < 2
                              ? t("crossRequiresTwoDocs")
                              : undefined
                          }
                          onClick={() => addFromLibrary(tpl.id)}
                        >
                          {added ? (
                            t("added")
                          ) : (
                            <>
                              <Plus className="h-3 w-3" />
                              {t("addRule")}
                            </>
                          )}
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
