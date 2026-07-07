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

/** Desktop table columns; minmax(0,…) lets cells shrink without overlapping neighbors. */
const SCHEMA_ROW_GRID =
  "md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,2fr)_2rem] md:gap-0";

const FIELD_LABEL_CLASS =
  "text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant md:sr-only";

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
      <SelectTrigger className="h-auto min-h-8 w-full min-w-0 py-1 text-xs border-transparent bg-transparent shadow-none focus:bg-card gap-2">
        <SelectValue className="sr-only" aria-label={label(current)} />
        <div className="flex min-w-0 flex-1 flex-col items-start text-left overflow-hidden">
          <span className="w-full truncate font-medium leading-tight">{label(current)}</span>
          <span className="w-full truncate text-[10px] text-on-surface-variant leading-tight">
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
    <div
      className={cn(
        "group flex flex-col gap-3 p-3 hover:bg-surface-bright transition-colors",
        "border-b border-border last:border-b-0 md:border-b-0",
        SCHEMA_ROW_GRID
      )}
    >
      <div className="flex flex-col gap-1 min-w-0 md:justify-center md:px-2 md:py-1 md:border-r md:border-border">
        <span className={FIELD_LABEL_CLASS}>{t("schema.name")}</span>
        <div className="flex items-center gap-1 min-w-0">
          <GripVertical className="hidden md:block h-3 w-3 text-outline-variant opacity-0 group-hover:opacity-60 cursor-grab shrink-0" />
          <Input
            value={field.name}
            onChange={(e) => onUpdate({ name: e.target.value })}
            placeholder={t("schema.namePlaceholder")}
            aria-invalid={isDuplicate}
            className={cn(
              "font-mono text-xs h-9 min-w-0 w-full border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input",
              isDuplicate && "border-danger text-danger focus-visible:border-danger"
            )}
          />
        </div>
        {isDuplicate ? (
          <p className="text-[10px] text-danger md:pl-4">{t("schema.duplicateName")}</p>
        ) : null}
      </div>
      <div className="flex flex-col gap-1 min-w-0 md:justify-center md:px-2 md:py-1 md:border-r md:border-border">
        <span className={FIELD_LABEL_CLASS}>{t("schema.type")}</span>
        <TemplateTypeSelect
          value={currentType}
          onChange={(templateType) => onUpdate({ templateType })}
          t={t}
        />
        {showSuggestion ? (
          <button
            type="button"
            onClick={() => onUpdate({ templateType: suggestedType! })}
            className="text-left text-[10px] text-primary hover:underline truncate max-w-full"
            title={t("schema.applySuggestedType")}
          >
            {t("schema.suggestedType", { label: label(suggestedType!) })}
          </button>
        ) : null}
      </div>
      <div className="flex flex-col gap-1 min-w-0 md:flex-row md:items-center md:px-2">
        <span className={FIELD_LABEL_CLASS}>{t("schema.intent")}</span>
        <Input
          value={field.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          placeholder={t("schema.descriptionPlaceholder")}
          className="text-xs h-9 min-w-0 w-full border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input"
        />
      </div>
      <div className="flex justify-end md:items-center md:justify-center md:self-stretch">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-outline hover:text-danger md:opacity-0 md:group-hover:opacity-100"
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
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <p className="text-[11px] text-on-surface-variant flex items-start gap-1.5 min-w-0">
          <Sparkles className="h-3 w-3 text-accent-blue shrink-0 mt-0.5" />
          <span className="min-w-0">{t("schema.description")}</span>
        </p>
        <Button variant="ghost" size="sm" className="h-7 text-xs shrink-0 self-end sm:self-auto" onClick={add}>
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
        <div className="border border-border rounded-lg overflow-hidden min-w-0">
          <div
            className={cn(
              "hidden md:grid bg-surface-container-low border-b border-border",
              SCHEMA_ROW_GRID
            )}
          >
            <div className="min-w-0 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant border-r border-border break-words leading-snug">
              {t("schema.name")}
            </div>
            <div className="min-w-0 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant border-r border-border break-words leading-snug">
              {t("schema.type")}
            </div>
            <div className="min-w-0 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant break-words leading-snug">
              {t("schema.intent")}
            </div>
            <div className="sr-only">{tCommon("delete")}</div>
          </div>
          <div className="md:divide-y md:divide-border">
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
