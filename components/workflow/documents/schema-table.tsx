"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { GripVertical, Plus, Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchSuggestedTemplateType } from "@/lib/api/suggest-template-type";
import {
  DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
  getSelectableTemplateTypes,
  getVisibleTemplateTypes,
  groupTemplateTypes,
  type NuExtractTemplateType,
  type NuExtractTypeGroup,
} from "@/lib/nuextract-types";
import type { SchemaField } from "@/lib/types";
import { normalizeSchemaFieldName } from "@/lib/workflow/schema-validation";
import { cn, shortId } from "@/lib/utils";

const TYPE_GROUPS: NuExtractTypeGroup[] = ["common", "advanced"];
const VISIBLE_TEMPLATE_TYPES = new Set(getVisibleTemplateTypes());

function useTypeLabels(t: ReturnType<typeof useTranslations>) {
  return useMemo(() => {
    const label = (value: string) => {
      if (!VISIBLE_TEMPLATE_TYPES.has(value as NuExtractTemplateType)) return value;
      return t(`schema.templateTypes.${value}.label` as "schema.templateTypes.verbatim-string.label");
    };
    const description = (value: string) => {
      if (!VISIBLE_TEMPLATE_TYPES.has(value as NuExtractTemplateType)) return "";
      return t(
        `schema.templateTypes.${value}.description` as "schema.templateTypes.verbatim-string.description"
      );
    };
    return { label, description };
  }, [t]);
}

function TemplateTypeSelect({
  value,
  onChange,
  t,
}: {
  value: string;
  onChange: (value: NuExtractTemplateType) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const { label, description } = useTypeLabels(t);
  const current = value || DEFAULT_NUEXTRACT_TEMPLATE_TYPE;
  const selectable = getSelectableTemplateTypes(current);
  const grouped = groupTemplateTypes(selectable);

  return (
    <Select value={current} onValueChange={(next) => onChange(next as NuExtractTemplateType)}>
      <SelectTrigger className="h-auto min-h-8 py-1 text-xs border-transparent bg-transparent shadow-none focus:bg-card">
        <SelectValue className="sr-only" aria-label={label(current)} />
        <div className="flex min-w-0 flex-col items-start text-left">
          <span className="truncate font-medium leading-tight">{label(current)}</span>
          <span className="truncate text-[10px] text-on-surface-variant leading-tight">
            {description(current)}
          </span>
        </div>
      </SelectTrigger>
      <SelectContent className="max-h-80 w-72">
        {TYPE_GROUPS.map((group) => {
          const types = grouped[group];
          if (types.length === 0) return null;
          return (
            <SelectGroup key={group}>
              <SelectLabel className="text-[10px]">{t(`schema.typeGroups.${group}`)}</SelectLabel>
              {types.map((typeValue) => (
                <SelectItem
                  key={typeValue}
                  value={typeValue}
                  textValue={label(typeValue)}
                  className="py-2"
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-medium leading-tight">{label(typeValue)}</span>
                    <span className="text-[10px] text-on-surface-variant leading-snug">
                      {description(typeValue)}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectGroup>
          );
        })}
      </SelectContent>
    </Select>
  );
}

function SchemaFieldRow({
  field,
  duplicateNames,
  onUpdate,
  onRemove,
  t,
  tCommon,
}: {
  field: SchemaField;
  duplicateNames: Set<string>;
  onUpdate: (patch: Partial<SchemaField>) => void;
  onRemove: () => void;
  t: ReturnType<typeof useTranslations>;
  tCommon: ReturnType<typeof useTranslations>;
}) {
  const { label } = useTypeLabels(t);
  const currentType = field.templateType || DEFAULT_NUEXTRACT_TEMPLATE_TYPE;
  const [suggestedType, setSuggestedType] = useState<string | null>(null);
  const normName = normalizeSchemaFieldName(field.name);
  const isDuplicate = normName.length > 0 && duplicateNames.has(normName);
  const hasIntent = field.name.trim().length > 0 || field.description.trim().length > 0;
  const showSuggestion =
    hasIntent && suggestedType !== null && suggestedType !== currentType;

  useEffect(() => {
    if (!hasIntent) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void fetchSuggestedTemplateType(field.name, field.description).then((value) => {
        if (!cancelled) setSuggestedType(value);
      });
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [field.name, field.description, hasIntent]);

  return (
    <div className="grid grid-cols-[minmax(150px,1fr)_minmax(180px,1.1fr)_minmax(220px,2fr)_32px] group hover:bg-surface-bright transition-colors">
      <div className="flex flex-col justify-center gap-1 px-2 border-r border-border">
        <div className="flex items-center gap-1">
          <GripVertical className="h-3 w-3 text-outline-variant opacity-0 group-hover:opacity-60 cursor-grab shrink-0" />
          <Input
            value={field.name}
            onChange={(e) => onUpdate({ name: e.target.value })}
            placeholder={t("schema.namePlaceholder")}
            aria-invalid={isDuplicate}
            className={cn(
              "font-mono text-xs h-9 border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input",
              isDuplicate && "border-danger text-danger focus-visible:border-danger"
            )}
          />
        </div>
        {isDuplicate ? (
          <p className="text-[10px] text-danger pl-4">{t("schema.duplicateName")}</p>
        ) : null}
      </div>
      <div className="px-2 py-1 flex flex-col justify-center gap-1 border-r border-border min-w-0">
        <TemplateTypeSelect
          value={currentType}
          onChange={(templateType) => onUpdate({ templateType })}
          t={t}
        />
        {showSuggestion ? (
          <button
            type="button"
            onClick={() => onUpdate({ templateType: suggestedType! })}
            className="text-left text-[10px] text-primary hover:underline truncate"
            title={t("schema.applySuggestedType")}
          >
            {t("schema.suggestedType", { label: label(suggestedType!) })}
          </button>
        ) : null}
      </div>
      <div className="px-2 flex items-center">
        <Input
          value={field.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          placeholder={t("schema.descriptionPlaceholder")}
          className="text-xs h-9 border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input"
        />
      </div>
      <div className="flex items-center justify-center">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-outline hover:text-danger opacity-0 group-hover:opacity-100"
          onClick={onRemove}
          aria-label={tCommon("delete")}
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

export function SchemaTable({
  schema,
  onChange,
  t,
}: {
  schema: SchemaField[];
  onChange: (schema: SchemaField[]) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const tCommon = useTranslations("common");
  const duplicateNames = useMemo(() => {
    const counts = new Map<string, number>();
    for (const field of schema) {
      const norm = normalizeSchemaFieldName(field.name);
      if (!norm) continue;
      counts.set(norm, (counts.get(norm) ?? 0) + 1);
    }
    return new Set(
      [...counts.entries()].filter(([, count]) => count > 1).map(([name]) => name)
    );
  }, [schema]);

  const update = (id: string, patch: Partial<SchemaField>) =>
    onChange(schema.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  const remove = (id: string) => onChange(schema.filter((f) => f.id !== id));
  const add = () =>
    onChange([
      ...schema,
      {
        id: `f${shortId()}`,
        name: "",
        description: "",
        templateType: DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
      },
    ]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-4">
        <p className="text-[11px] text-on-surface-variant flex items-center gap-1.5">
          <Sparkles className="h-3 w-3 text-accent-blue shrink-0" />
          {t("schema.description")}
        </p>
        <Button variant="ghost" size="sm" className="h-7 text-xs shrink-0" onClick={add}>
          <Plus className="h-3 w-3" />
          {t("schema.addField")}
        </Button>
      </div>

      {schema.length === 0 ? (
        <button
          type="button"
          onClick={add}
          className="w-full border-2 border-dashed border-outline-variant rounded-lg py-8 text-center text-xs text-on-surface-variant hover:border-primary/40 hover:bg-primary/5 transition-colors"
        >
          {t("schema.empty")}
        </button>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="grid grid-cols-[minmax(150px,1fr)_minmax(180px,1.1fr)_minmax(220px,2fr)_32px] gap-0 bg-surface-container-low border-b border-border">
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant border-r border-border">
              {t("schema.name")}
            </div>
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant border-r border-border">
              {t("schema.type")}
            </div>
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              {t("schema.intent")}
            </div>
          </div>
          <div className="divide-y divide-border">
            {schema.map((f) => (
              <SchemaFieldRow
                key={f.id}
                field={f}
                duplicateNames={duplicateNames}
                onUpdate={(patch) => update(f.id, patch)}
                onRemove={() => remove(f.id)}
                t={t}
                tCommon={tCommon}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
