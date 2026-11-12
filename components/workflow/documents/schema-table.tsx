"use client";

import { FileJson2, Plus, Sparkles, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ImportNuextractTemplateDialog } from "@/components/workflow/documents/import-nuextract-template-dialog";
import { SchemaFieldExtraConfig } from "@/components/workflow/documents/schema-field-extra";
import {
  ListToggle,
  TemplateTypeSelect,
} from "@/components/workflow/documents/template-type-select";
import { fieldKey } from "@/lib/rules/field-key";
import type { SchemaField } from "@/lib/types";
import { cn } from "@/lib/utils";
import { newSchemaField } from "@/lib/workflow/new-items";

/** Desktop table columns; minmax(0,…) lets cells shrink without overlapping neighbors. */
const ROW_GRID =
  "md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,2fr)_auto_2rem] md:gap-0";
const CELL =
  "flex flex-col gap-1 min-w-0 md:justify-center md:px-2 md:py-1 md:border-r md:border-line";
const MOBILE_LABEL = "text-2xs font-semibold text-ink-3 md:sr-only";
const HEADER_CELL =
  "min-w-0 px-3 py-2 text-2xs font-semibold text-ink-3 border-r border-line break-words leading-snug";
const INLINE_INPUT =
  "text-xs h-9 min-w-0 w-full border-transparent bg-transparent shadow-none focus-visible:bg-panel focus-visible:border-line-strong";

function SchemaFieldRow({
  field,
  duplicate,
  onUpdate,
  onRemove,
}: {
  field: SchemaField;
  duplicate: boolean;
  onUpdate: (patch: Partial<SchemaField>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const tCommon = useTranslations("common");

  return (
    <div className="border-b border-line last:border-b-0 md:border-b-0">
      <div
        className={cn("group flex flex-col gap-3 p-3 hover:bg-panel transition-colors", ROW_GRID)}
      >
        <div className={CELL}>
          <span className={MOBILE_LABEL}>{t("name")}</span>
          <Input
            value={field.name}
            onChange={(e) => onUpdate({ name: e.target.value })}
            placeholder={t("namePlaceholder")}
            aria-invalid={duplicate}
            className={cn(
              "font-mono",
              INLINE_INPUT,
              duplicate && "border-fail text-fail-ink focus-visible:border-fail"
            )}
          />
          {duplicate ? <p className="text-2xs text-fail-ink">{t("duplicateName")}</p> : null}
        </div>
        <div className={CELL}>
          <span className={MOBILE_LABEL}>{t("type")}</span>
          <TemplateTypeSelect
            detailed
            value={field.templateType}
            onChange={(templateType) => onUpdate({ templateType })}
          />
        </div>
        <div className={cn(CELL, "md:flex-row md:items-center")}>
          <span className={MOBILE_LABEL}>{t("intent")}</span>
          <Input
            value={field.description}
            onChange={(e) => onUpdate({ description: e.target.value })}
            placeholder={t("descriptionPlaceholder")}
            className={INLINE_INPUT}
          />
        </div>
        <div className={cn(CELL, "md:items-center")}>
          <ListToggle
            value={field.templateType}
            onChange={(templateType) => onUpdate({ templateType })}
            className="justify-end md:justify-center whitespace-nowrap"
          />
        </div>
        <div className="flex justify-end md:items-center md:justify-center md:self-stretch">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-outline hover:text-fail-ink md:opacity-0 md:group-hover:opacity-100 focus-visible:opacity-100"
            onClick={onRemove}
            aria-label={tCommon("delete")}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
      <SchemaFieldExtraConfig field={field} onUpdate={onUpdate} />
    </div>
  );
}

export function SchemaTable({
  schema,
  onChange,
}: {
  schema: SchemaField[];
  onChange: (schema: SchemaField[]) => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const tCommon = useTranslations("common");
  const [importOpen, setImportOpen] = useState(false);
  // Names that address the same field (the API matches names by `field_key`).
  const duplicates = useMemo(() => {
    const keys = schema.map((field) => fieldKey(field.name)).filter(Boolean);
    return new Set(keys.filter((key, i) => keys.indexOf(key) !== i));
  }, [schema]);

  const update = (id: string, patch: Partial<SchemaField>) =>
    onChange(schema.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  const add = () => onChange([...schema, newSchemaField()]);

  return (
    <div className="space-y-2">
      <ImportNuextractTemplateDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        hasExistingFields={schema.some((f) => f.name.trim())}
        onImport={(fields, mode) => onChange(mode === "append" ? [...schema, ...fields] : fields)}
      />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <p className="text-2xs text-ink-3 flex items-start gap-1.5 min-w-0">
          <Sparkles className="h-3 w-3 text-accent-ink shrink-0 mt-0.5" />
          <span className="min-w-0">{t("description")}</span>
        </p>
        <div className="flex shrink-0 items-center gap-1 self-end sm:self-auto">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setImportOpen(true)}
          >
            <FileJson2 className="h-3 w-3" />
            {t("importTemplate")}
          </Button>
          <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={add}>
            <Plus className="h-3 w-3" />
            {t("addField")}
          </Button>
        </div>
      </div>

      {schema.length === 0 ? (
        <button
          type="button"
          onClick={add}
          className="w-full border-2 border-dashed border-line rounded-lg py-8 text-center text-xs text-ink-3 hover:border-accent/40 hover:bg-accent/5 transition-colors"
        >
          {t("empty")}
        </button>
      ) : (
        <div className="border border-line rounded-lg overflow-hidden min-w-0">
          <div className={cn("hidden md:grid bg-raised border-b border-line", ROW_GRID)}>
            <div className={HEADER_CELL}>{t("name")}</div>
            <div className={HEADER_CELL}>{t("type")}</div>
            <div className={HEADER_CELL}>{t("intent")}</div>
            <div className={cn(HEADER_CELL, "md:text-center")}>{t("listModeLabel")}</div>
            <div className="sr-only">{tCommon("delete")}</div>
          </div>
          <div className="md:divide-y md:divide-line">
            {schema.map((field) => (
              <SchemaFieldRow
                key={field.id}
                field={field}
                duplicate={duplicates.has(fieldKey(field.name))}
                onUpdate={(patch) => update(field.id, patch)}
                onRemove={() => onChange(schema.filter((f) => f.id !== field.id))}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
