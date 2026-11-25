"use client";

import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { BareInput } from "@/components/ui/input";
import {
  ListToggle,
  TemplateTypeSelect,
} from "@/components/workflow/documents/template-type-select";
import type { SchemaField } from "@/lib/types";
import { cn } from "@/lib/utils";
import { newSchemaField } from "@/lib/workflow/new-items";

/** The fields table grid; nested rows (object fields, table columns) share it. */
export const FIELD_GRID =
  "md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,2fr)_28px_28px] md:items-center md:gap-2";

/** A cell input that looks like text until hovered or focused. */
export const CELL_INPUT =
  "h-7 w-full min-w-0 rounded-md bg-transparent px-2 text-[13px] text-ink outline-none transition-colors duration-100 placeholder:text-ink-4 hover:bg-hover focus-visible:bg-field focus-visible:shadow-[inset_0_0_0_1px_var(--accent)] focus-visible:outline-none";

/** Nested content hangs off its field on a rail, indented one step. */
function Nested({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="ms-4 mb-2 flex flex-col gap-0.5 border-s border-line ps-3 md:ms-6">
      <span className="px-2 pt-1 text-xs text-ink-3">{label}</span>
      {children}
    </div>
  );
}

/** The choices of an enum or multi-enum. */
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
    <Nested label={t("enumValuesLabel")}>
      <ul className="flex flex-col">
        {rows.map((value, index) => (
          // Choices are edited in place and never reordered: the position is their identity.
          // oxlint-disable-next-line react/no-array-index-key -- index is the row identity
          <li key={`enum-${index}`} className="group flex max-w-sm items-center gap-1">
            <BareInput
              value={value}
              onChange={(e) => {
                const next = [...rows];
                next[index] = e.target.value;
                onChange(next.filter((row, i) => row.trim() || i < next.length - 1));
              }}
              placeholder={t("enumValuePlaceholder")}
              aria-label={t("enumValuesLabel")}
              className={CELL_INPUT}
            />
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-ink-4 hover:text-fail-ink pointer-fine:opacity-0 pointer-fine:group-focus-within:opacity-100 pointer-fine:group-hover:opacity-100"
              onClick={() => onChange(rows.filter((_, i) => i !== index))}
              aria-label={t("removeEnumValue")}
            >
              <X />
            </Button>
          </li>
        ))}
      </ul>
      <Button
        variant="ghost"
        size="sm"
        className="self-start"
        onClick={() => onChange([...rows.filter((v) => v.trim()), ""])}
      >
        <Plus />
        {t("addEnumValue")}
      </Button>
    </Nested>
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
    <Nested label={table ? t("rowColumnsLabel") : t("objectFieldsLabel")}>
      {fields.length === 0 ? (
        <p className="px-2 py-1 text-sm text-ink-4">
          {table ? t("rowColumnsEmpty") : t("objectFieldsEmpty")}
        </p>
      ) : (
        <ul className="flex flex-col">
          {fields.map((child) => (
            <li key={child.id} className="group">
              <div className={cn("flex flex-col gap-1 py-0.5", FIELD_GRID)}>
                <BareInput
                  value={child.name}
                  onChange={(e) => update(child.id, { name: e.target.value })}
                  placeholder={t("namePlaceholder")}
                  aria-label={t("name")}
                  className={cn(CELL_INPUT, "font-mono text-xs")}
                />
                <TemplateTypeSelect
                  value={child.templateType}
                  structures={!table}
                  onChange={(templateType) => update(child.id, { templateType })}
                />
                <BareInput
                  value={child.description}
                  onChange={(e) => update(child.id, { description: e.target.value })}
                  placeholder={t("descriptionPlaceholder")}
                  aria-label={t("intent")}
                  className={CELL_INPUT}
                />
                <ListToggle
                  value={child.templateType}
                  onChange={(templateType) => update(child.id, { templateType })}
                />
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="text-ink-4 hover:text-fail-ink pointer-fine:opacity-0 pointer-fine:group-focus-within:opacity-100 pointer-fine:group-hover:opacity-100"
                  onClick={() => onChange(fields.filter((row) => row.id !== child.id))}
                  aria-label={table ? t("removeRowColumn") : t("removeObjectField")}
                >
                  <X />
                </Button>
              </div>
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
        variant="ghost"
        size="sm"
        className="self-start"
        onClick={() => onChange([...fields, newSchemaField()])}
      >
        <Plus />
        {table ? t("addRowColumn") : t("addObjectField")}
      </Button>
    </Nested>
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
      <EnumValuesEditor
        values={field.enumValues}
        onChange={(enumValues) => onUpdate({ enumValues })}
      />
    );
  }
  if (type === "object" || type === "object-array") {
    return (
      <ChildrenEditor
        fields={field.children}
        onChange={(children) => onUpdate({ children })}
        mode={type}
      />
    );
  }
  return null;
}
