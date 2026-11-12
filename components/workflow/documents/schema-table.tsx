"use client";

import { FileJson2, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
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

const GRID =
  "md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,2fr)_88px_28px] md:items-center md:gap-2";

/** A cell input that looks like text until hovered or focused. */
const CELL_INPUT =
  "h-8 w-full min-w-0 rounded-md bg-transparent px-2 text-sm text-ink outline-none transition-colors duration-100 placeholder:text-ink-4 hover:bg-hover focus-visible:bg-field focus-visible:shadow-[inset_0_0_0_1px_var(--accent)] focus-visible:outline-none";

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
    <li className="group">
      <div className={cn("flex flex-col gap-1 px-2 py-1.5 md:py-1", GRID)}>
        <div className="min-w-0">
          <input
            value={field.name}
            onChange={(e) => onUpdate({ name: e.target.value })}
            placeholder={t("namePlaceholder")}
            aria-label={t("name")}
            aria-invalid={duplicate}
            className={cn(CELL_INPUT, "font-mono text-xs", duplicate && "text-fail-ink")}
          />
          {duplicate ? <p className="px-2 text-xs text-fail-ink">{t("duplicateName")}</p> : null}
        </div>
        <TemplateTypeSelect
          value={field.templateType}
          onChange={(templateType) => onUpdate({ templateType })}
        />
        <input
          value={field.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          placeholder={t("descriptionPlaceholder")}
          aria-label={t("intent")}
          className={CELL_INPUT}
        />
        <ListToggle
          value={field.templateType}
          onChange={(templateType) => onUpdate({ templateType })}
        />
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-ink-4 hover:text-fail-ink md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100"
          onClick={onRemove}
          aria-label={tCommon("delete")}
        >
          <X />
        </Button>
      </div>
      <SchemaFieldExtraConfig field={field} onUpdate={onUpdate} />
    </li>
  );
}

/** The fields to read from a document: name, how the value is written, what it is. */
export function SchemaTable({
  schema,
  onChange,
}: {
  schema: SchemaField[];
  onChange: (schema: SchemaField[]) => void;
}) {
  const t = useTranslations("workflows.builder.schema");
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
    <div className="flex flex-col gap-2">
      <ImportNuextractTemplateDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        hasExistingFields={schema.some((f) => f.name.trim())}
        onImport={(fields, mode) => onChange(mode === "append" ? [...schema, ...fields] : fields)}
      />
      <div className="overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]">
        <div
          className={cn(
            "hidden h-8 border-b border-line bg-raised px-2 text-xs font-medium text-ink-3",
            GRID
          )}
        >
          <span className="px-2">{t("name")}</span>
          <span className="px-2">{t("type")}</span>
          <span className="px-2">{t("intent")}</span>
          <span className="px-2 text-center">{t("listModeLabel")}</span>
          <span />
        </div>
        {schema.length ? (
          <ul className="divide-y divide-line">
            {schema.map((field) => (
              <SchemaFieldRow
                key={field.id}
                field={field}
                duplicate={duplicates.has(fieldKey(field.name))}
                onUpdate={(patch) => update(field.id, patch)}
                onRemove={() => onChange(schema.filter((f) => f.id !== field.id))}
              />
            ))}
          </ul>
        ) : (
          <p className="px-4 py-6 text-sm text-ink-3">{t("empty")}</p>
        )}
        <div className="flex items-center gap-1 border-t border-line px-2 py-1">
          <Button variant="ghost" size="sm" onClick={add}>
            <Plus />
            {t("addField")}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setImportOpen(true)}>
            <FileJson2 />
            {t("importTemplate")}
          </Button>
        </div>
      </div>
    </div>
  );
}
