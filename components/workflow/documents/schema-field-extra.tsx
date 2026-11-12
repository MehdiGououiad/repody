"use client";

import { Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ListToggle,
  TemplateTypeSelect,
} from "@/components/workflow/documents/template-type-select";
import type { SchemaField } from "@/lib/types";
import { newSchemaField } from "@/lib/workflow/new-items";

const FIELD_LABEL = "text-2xs font-semibold text-ink-3";

/** The choices of an enum or multi-enum; an empty last row adds the next choice. */
function EnumValuesEditor({
  values,
  onChange,
}: {
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const rows = values.length > 0 ? values : [""];

  return (
    <div className="space-y-2 rounded-lg border border-dashed border-line/80 bg-raised/40 p-3">
      <p className={FIELD_LABEL}>{t("enumValuesLabel")}</p>
      {rows.map((value, index) => (
        // Choices are edited in place and never reordered: the position is their identity.
        // biome-ignore lint/suspicious/noArrayIndexKey: index is the row identity
        <div key={`enum-${index}`} className="flex items-center gap-2">
          <Input
            value={value}
            onChange={(e) => {
              const next = [...rows];
              next[index] = e.target.value;
              onChange(next.filter((row, i) => row.trim() || i < next.length - 1));
            }}
            placeholder={t("enumValuePlaceholder")}
            className="h-8 text-xs"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-ink-4 hover:text-fail-ink"
            onClick={() => onChange(rows.filter((_, i) => i !== index))}
            aria-label={t("removeEnumValue")}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 text-2xs"
        onClick={() => onChange([...rows.filter((v) => v.trim()), ""])}
      >
        <Plus className="h-3 w-3" />
        {t("addEnumValue")}
      </Button>
    </div>
  );
}

/** The fields of an object, or the columns of an object-array (scalars only). */
function ChildrenEditor({
  fields,
  onChange,
  mode,
}: {
  fields: SchemaField[];
  onChange: (fields: SchemaField[]) => void;
  mode: "object" | "object-array";
}) {
  const t = useTranslations("workflows.builder.schema");
  const table = mode === "object-array";
  const update = (id: string, patch: Partial<SchemaField>) =>
    onChange(fields.map((child) => (child.id === id ? { ...child, ...patch } : child)));

  return (
    <div className="space-y-3 rounded-xl border border-accent/15 bg-accent/[0.03] p-3 sm:p-4">
      <div className="space-y-1">
        <p className="text-2xs font-semibold text-ink">
          {table ? t("rowColumnsLabel") : t("objectFieldsLabel")}
        </p>
        <p className="text-2xs leading-snug text-ink-3">
          {table ? t("rowColumnsHint") : t("objectFieldsHint")}
        </p>
      </div>

      {fields.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line/80 bg-panel/50 px-3 py-4 text-center text-2xs text-ink-3">
          {table ? t("rowColumnsEmpty") : t("objectFieldsEmpty")}
        </p>
      ) : (
        <ul className="space-y-2">
          {fields.map((child, index) => (
            <li
              key={child.id}
              className="rounded-lg border border-line/70 bg-panel p-3 shadow-black/[0.02]"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className={FIELD_LABEL}>
                  {table
                    ? t("rowColumnIndex", { index: index + 1 })
                    : t("objectFieldIndex", { index: index + 1 })}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-ink-4 hover:text-fail-ink"
                  onClick={() => onChange(fields.filter((row) => row.id !== child.id))}
                  aria-label={table ? t("removeRowColumn") : t("removeObjectField")}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="space-y-1 min-w-0">
                  <span className={FIELD_LABEL}>{t("name")}</span>
                  <Input
                    value={child.name}
                    onChange={(e) => update(child.id, { name: e.target.value })}
                    placeholder={t("namePlaceholder")}
                    className="h-9 font-mono text-xs"
                  />
                </label>
                <div className="space-y-1 min-w-0">
                  <span className={FIELD_LABEL}>{t("type")}</span>
                  <TemplateTypeSelect
                    value={child.templateType}
                    structures={!table}
                    onChange={(templateType) => update(child.id, { templateType })}
                  />
                </div>
              </div>
              <label className="mt-2 block space-y-1">
                <span className={FIELD_LABEL}>{t("intent")}</span>
                <Input
                  value={child.description}
                  onChange={(e) => update(child.id, { description: e.target.value })}
                  placeholder={t("descriptionPlaceholder")}
                  className="h-9 text-xs"
                />
              </label>
              <ListToggle
                value={child.templateType}
                onChange={(templateType) => update(child.id, { templateType })}
                className="mt-2 text-2xs"
              />
              {!table ? (
                <SchemaFieldExtraConfig
                  field={child}
                  onUpdate={(patch) => update(child.id, patch)}
                />
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 w-full text-2xs sm:w-auto"
        onClick={() => onChange([...fields, newSchemaField()])}
      >
        <Plus className="h-3.5 w-3.5" />
        {table ? t("addRowColumn") : t("addObjectField")}
      </Button>
    </div>
  );
}

/** What a structure type needs beyond its name: choices, or child fields. Nothing for leaves. */
export function SchemaFieldExtraConfig({
  field,
  onUpdate,
}: {
  field: SchemaField;
  onUpdate: (patch: Partial<SchemaField>) => void;
}) {
  const type = field.templateType;
  if (type === "enum" || type === "multi-enum") {
    return (
      <div className="px-3 pb-3">
        <EnumValuesEditor
          values={field.enumValues}
          onChange={(enumValues) => onUpdate({ enumValues })}
        />
      </div>
    );
  }
  if (type === "object" || type === "object-array") {
    return (
      <div className="px-3 pb-3">
        <ChildrenEditor
          fields={field.children}
          onChange={(children) => onUpdate({ children })}
          mode={type}
        />
      </div>
    );
  }
  return null;
}
