"use client";

import { Plus, Trash2 } from "lucide-react";
import type { useTranslations } from "next-intl";
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
  type NuExtractTemplateType,
  type NuExtractTypeGroup,
  scalarTemplateType,
  supportsListTemplateType,
  withListTemplateType,
} from "@/lib/nuextract-types";
import type { SchemaField } from "@/lib/types";
import { shortId } from "@/lib/utils";

const CHILD_TYPE_GROUPS: NuExtractTypeGroup[] = ["common", "advanced"];

function childTypeLabel(t: ReturnType<typeof useTranslations>, value: string) {
  const scalar = scalarTemplateType(value);
  const key =
    `schema.templateTypes.${scalar}.label` as "schema.templateTypes.verbatim-string.label";
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
        // Enum rows are edited in place by index and never reordered, so the
        // position is the only stable identity available here.
        // biome-ignore lint/suspicious/noArrayIndexKey: index is the row identity
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

function NestedChildrenEditor({
  fields,
  onChange,
  t,
  mode,
}: {
  fields: SchemaField[];
  onChange: (fields: SchemaField[]) => void;
  t: ReturnType<typeof useTranslations>;
  mode: "object" | "object-array";
}) {
  const grouped = groupTemplateTypes(
    getSelectableTemplateTypes().filter((type) => {
      if (mode === "object-array") {
        return (
          type !== "object-array" && type !== "object" && type !== "enum" && type !== "multi-enum"
        );
      }
      // Nested object groups may themselves nest further objects / tables / enums.
      return true;
    })
  );
  const typeGroups: NuExtractTypeGroup[] =
    mode === "object-array" ? CHILD_TYPE_GROUPS : ["common", "structure", "advanced"];

  const updateChild = (id: string, patch: Partial<SchemaField>) => {
    onChange(fields.map((child) => (child.id === id ? { ...child, ...patch } : child)));
  };

  const title = mode === "object" ? t("schema.objectFieldsLabel") : t("schema.rowColumnsLabel");
  const hint = mode === "object" ? t("schema.objectFieldsHint") : t("schema.rowColumnsHint");
  const addLabel = mode === "object" ? t("schema.addObjectField") : t("schema.addRowColumn");
  const removeLabel =
    mode === "object" ? t("schema.removeObjectField") : t("schema.removeRowColumn");

  return (
    <div className="space-y-3 rounded-xl border border-primary/15 bg-primary/[0.03] p-3 sm:p-4">
      <div className="space-y-1">
        <p className="text-[11px] font-semibold tracking-wide text-on-surface">{title}</p>
        <p className="text-[11px] leading-snug text-on-surface-variant">{hint}</p>
      </div>

      {fields.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border/80 bg-card/50 px-3 py-4 text-center text-[11px] text-on-surface-variant">
          {mode === "object" ? t("schema.objectFieldsEmpty") : t("schema.rowColumnsEmpty")}
        </p>
      ) : (
        <ul className="space-y-2">
          {fields.map((child, index) => {
            const childType = child.templateType || DEFAULT_NUEXTRACT_TEMPLATE_TYPE;
            const childListMode = isListTemplateType(childType);
            return (
              <li
                key={child.id}
                className="rounded-lg border border-border/70 bg-card p-3 shadow-sm shadow-black/[0.02]"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    {mode === "object-array"
                      ? t("schema.rowColumnIndex", { index: index + 1 })
                      : t("schema.objectFieldIndex", { index: index + 1 })}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-outline hover:text-danger"
                    onClick={() => onChange(fields.filter((row) => row.id !== child.id))}
                    aria-label={removeLabel}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <label className="space-y-1 min-w-0">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                      {t("schema.name")}
                    </span>
                    <Input
                      value={child.name}
                      onChange={(e) => updateChild(child.id, { name: e.target.value })}
                      placeholder={t("schema.namePlaceholder")}
                      className="h-9 font-mono text-xs"
                    />
                  </label>
                  <label className="space-y-1 min-w-0">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                      {t("schema.type")}
                    </span>
                    <Select
                      value={scalarTemplateType(childType)}
                      onValueChange={(templateType) =>
                        updateChild(child.id, {
                          templateType: withListTemplateType(
                            templateType,
                            childListMode
                          ) as NuExtractTemplateType,
                        })
                      }
                    >
                      <SelectTrigger className="h-9 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="max-h-72">
                        {typeGroups.map((group) => {
                          const types = grouped[group];
                          if (types.length === 0) return null;
                          return (
                            <SelectGroup key={group}>
                              <SelectLabel className="text-[10px]">
                                {t(`schema.typeGroups.${group}`)}
                              </SelectLabel>
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
                  </label>
                </div>
                <label className="mt-2 block space-y-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    {t("schema.intent")}
                  </span>
                  <Input
                    value={child.description}
                    onChange={(e) => updateChild(child.id, { description: e.target.value })}
                    placeholder={t("schema.descriptionPlaceholder")}
                    className="h-9 text-xs"
                  />
                </label>
                <label className="mt-2 flex items-center gap-2 text-[11px] text-on-surface-variant">
                  <input
                    type="checkbox"
                    className="size-3.5 rounded border-border text-primary focus-visible:ring-2 focus-visible:ring-ring/30"
                    checked={childListMode}
                    disabled={!supportsListTemplateType(childType)}
                    onChange={(e) =>
                      updateChild(child.id, {
                        templateType: withListTemplateType(childType, e.target.checked),
                      })
                    }
                  />
                  <span title={t("schema.listModeHint")}>{t("schema.listModeLabel")}</span>
                </label>
              </li>
            );
          })}
        </ul>
      )}

      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 w-full text-[11px] sm:w-auto"
        onClick={() =>
          onChange([
            ...fields,
            {
              id: `f${shortId()}`,
              name: "",
              description: "",
              templateType: DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
            },
          ])
        }
      >
        <Plus className="h-3.5 w-3.5" />
        {addLabel}
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

  if (templateType === "object" || templateType === "object-array") {
    return (
      <NestedChildrenEditor
        fields={field.children ?? []}
        onChange={(children) => onUpdate({ children })}
        t={t}
        mode={templateType}
      />
    );
  }

  return null;
}

export function schemaFieldNeedsExtra(templateType?: string) {
  return isStructureTemplateType(templateType);
}
