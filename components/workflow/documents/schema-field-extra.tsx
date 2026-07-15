"use client";

import { Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
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
import {
  DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
  getSelectableTemplateTypes,
  groupTemplateTypes,
  isListTemplateType,
  isStructureTemplateType,
  scalarTemplateType,
  withListTemplateType,
  type NuExtractTemplateType,
  type NuExtractTypeGroup,
} from "@/lib/nuextract-types";
import type { SchemaField } from "@/lib/types";
import { cn, shortId } from "@/lib/utils";

const CHILD_TYPE_GROUPS: NuExtractTypeGroup[] = ["common", "advanced"];

function childTypeLabel(t: ReturnType<typeof useTranslations>, value: string) {
  const scalar = scalarTemplateType(value);
  const key = `schema.templateTypes.${scalar}.label` as "schema.templateTypes.verbatim-string.label";
  try {
    return isListTemplateType(value) ? `${t(key)} · ${t("schema.listModeSuffix")}` : t(key);
  } catch {
    return value;
  }
}

function EnumValuesEditor({
  values,
  onChange,
  t,
}: {
  values: string[];
  onChange: (values: string[]) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const rows = values.length > 0 ? values : [""];

  return (
    <div className="space-y-2 rounded-lg border border-dashed border-border/80 bg-surface-container-low/40 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
        {t("schema.enumValuesLabel")}
      </p>
      {rows.map((value, index) => (
        <div key={`enum-${index}`} className="flex items-center gap-2">
          <Input
            value={value}
            onChange={(e) => {
              const next = [...rows];
              next[index] = e.target.value;
              onChange(next.filter((row, i) => row.trim() || i < next.length - 1));
            }}
            placeholder={t("schema.enumValuePlaceholder")}
            className="h-8 text-xs"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-outline hover:text-danger"
            onClick={() => onChange(rows.filter((_, i) => i !== index))}
            aria-label={t("schema.removeEnumValue")}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 text-[11px]"
        onClick={() => onChange([...rows.filter((v) => v.trim()), ""])}
      >
        <Plus className="h-3 w-3" />
        {t("schema.addEnumValue")}
      </Button>
    </div>
  );
}

function ObjectArrayChildrenEditor({
  children,
  onChange,
  t,
}: {
  children: SchemaField[];
  onChange: (children: SchemaField[]) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const grouped = groupTemplateTypes(
    getSelectableTemplateTypes().filter((type) => type !== "object-array" && type !== "enum" && type !== "multi-enum")
  );

  const updateChild = (id: string, patch: Partial<SchemaField>) => {
    onChange(children.map((child) => (child.id === id ? { ...child, ...patch } : child)));
  };

  return (
    <div className="space-y-2 rounded-lg border border-dashed border-primary/20 bg-primary/5 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
        {t("schema.rowColumnsLabel")}
      </p>
      {children.map((child) => {
        const childType = child.templateType || DEFAULT_NUEXTRACT_TEMPLATE_TYPE;
        const childListMode = isListTemplateType(childType);
        return (
        <div
          key={child.id}
          className="grid gap-2 rounded-md border border-border/70 bg-card/80 p-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.2fr)_auto_2rem]"
        >
          <Input
            value={child.name}
            onChange={(e) => updateChild(child.id, { name: e.target.value })}
            placeholder={t("schema.namePlaceholder")}
            className="h-8 font-mono text-xs"
          />
          <Select
            value={scalarTemplateType(childType)}
            onValueChange={(templateType) =>
              updateChild(child.id, {
                templateType: withListTemplateType(templateType, childListMode) as NuExtractTemplateType,
              })
            }
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="max-h-72">
              {CHILD_TYPE_GROUPS.map((group) => {
                const types = grouped[group];
                if (types.length === 0) return null;
                return (
                  <SelectGroup key={group}>
                    <SelectLabel className="text-[10px]">{t(`schema.typeGroups.${group}`)}</SelectLabel>
                    {types.map((typeValue) => (
                      <SelectItem key={typeValue} value={typeValue}>
                        {childTypeLabel(t, typeValue)}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                );
              })}
            </SelectContent>
          </Select>
          <Input
            value={child.description}
            onChange={(e) => updateChild(child.id, { description: e.target.value })}
            placeholder={t("schema.descriptionPlaceholder")}
            className="h-8 text-xs"
          />
          <label className="flex items-center justify-end gap-1.5 px-1 text-[10px] text-on-surface-variant whitespace-nowrap sm:justify-center">
            <input
              type="checkbox"
              className="size-3.5 rounded border-border text-primary focus-visible:ring-2 focus-visible:ring-ring/30"
              checked={childListMode}
              onChange={(e) =>
                updateChild(child.id, {
                  templateType: withListTemplateType(childType, e.target.checked),
                })
              }
              title={t("schema.listModeHint")}
            />
            {t("schema.listModeLabel")}
          </label>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-outline hover:text-danger"
            onClick={() => onChange(children.filter((row) => row.id !== child.id))}
            aria-label={t("schema.removeRowColumn")}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
        );
      })}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 text-[11px]"
        onClick={() =>
          onChange([
            ...children,
            {
              id: `f${shortId()}`,
              name: "",
              description: "",
              templateType: DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
            },
          ])
        }
      >
        <Plus className="h-3 w-3" />
        {t("schema.addRowColumn")}
      </Button>
    </div>
  );
}

export function SchemaFieldExtraConfig({
  field,
  onUpdate,
  t,
}: {
  field: SchemaField;
  onUpdate: (patch: Partial<SchemaField>) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const templateType = field.templateType || DEFAULT_NUEXTRACT_TEMPLATE_TYPE;

  if (templateType === "enum" || templateType === "multi-enum") {
    return (
      <EnumValuesEditor
        values={field.enumValues ?? []}
        onChange={(enumValues) => onUpdate({ enumValues })}
        t={t}
      />
    );
  }

  if (templateType === "object-array") {
    return (
      <ObjectArrayChildrenEditor
        children={field.children ?? []}
        onChange={(children) => onUpdate({ children })}
        t={t}
      />
    );
  }

  return null;
}

export function schemaFieldNeedsExtra(templateType?: string) {
  return isStructureTemplateType(templateType);
}
