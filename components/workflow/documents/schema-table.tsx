"use client";

import { FileJson2, Plus, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { BareInput } from "@/components/ui/input";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { ImportNuextractTemplateDialog } from "@/components/workflow/documents/import-nuextract-template-dialog";
import {
  CELL_INPUT,
  SchemaFieldExtraConfig,
} from "@/components/workflow/documents/schema-field-extra";
import {
  ListToggle,
  TemplateTypeSelect,
} from "@/components/workflow/documents/template-type-select";
import { EASE_OUT } from "@/lib/motion";
import { fieldKey } from "@/lib/rules/field-key";
import type { SchemaField } from "@/lib/types";
import { cn, formatExtractedFieldValue } from "@/lib/utils";
import { newSchemaField } from "@/lib/workflow/new-items";

/** What the last extraction found for a field: its value, or nothing. */
export type FieldResult = { extracted: boolean; value: unknown };

const ROW_GRID = "grid grid-cols-[14px_minmax(0,1fr)_minmax(0,1fr)] items-center gap-x-2";

/** A field's value from the sample, landing with a short status wash. */
function FieldValue({ result, stale }: { result: FieldResult | undefined; stale: boolean }) {
  const t = useTranslations("workflows.builder.schema");
  const locale = useLocale();
  if (!result) return <span className="truncate text-xs text-ink-4">—</span>;
  const text = result.extracted ? formatExtractedFieldValue(result.value, locale) : t("notFound");
  return (
    <AnimatePresence mode="popLayout" initial={false}>
      <motion.span
        key={text}
        initial={{ opacity: 0, y: 3 }}
        animate={{ opacity: stale ? 0.45 : 1, y: 0 }}
        transition={{ duration: 0.16, ease: EASE_OUT }}
        title={stale ? t("stale") : text}
        className={cn(
          "truncate rounded-sm px-1.5 py-0.5 text-[13px] tabular-nums",
          result.extracted ? "font-medium text-ink" : "text-warn-ink",
          !stale &&
            (result.extracted
              ? "animate-[wash-pass_0.8s_ease-out]"
              : "animate-[wash-warn_0.8s_ease-out]")
        )}
      >
        {text}
      </motion.span>
    </AnimatePresence>
  );
}

function SchemaFieldRow({
  field,
  duplicate,
  result,
  stale,
  focusName,
  onUpdate,
  onRemove,
}: {
  field: SchemaField;
  duplicate: boolean;
  /** A field just added: its name takes the focus. */
  focusName: boolean;
  result: FieldResult | undefined;
  stale: boolean;
  onUpdate: (patch: Partial<SchemaField>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const missing = result && !result.extracted && !stale;
  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, transition: { duration: 0.12 } }}
      transition={{ duration: 0.18, ease: EASE_OUT }}
      className={cn("group relative px-2 py-1.5", missing && "bg-warn-wash/40")}
    >
      <div className={ROW_GRID}>
        <StatusGlyph
          status={!result || stale ? "waiting" : result.extracted ? "passed" : "warning"}
          className="justify-self-center"
        />
        <div className="flex min-w-0 items-center gap-1">
          <BareInput
            value={field.name}
            onChange={(e) => onUpdate({ name: e.target.value })}
            placeholder={t("namePlaceholder")}
            aria-label={t("name")}
            autoFocus={focusName}
            aria-invalid={duplicate}
            className={cn(CELL_INPUT, "font-mono text-xs", duplicate && "text-fail-ink")}
          />
        </div>
        <div className="flex min-w-0 items-center justify-end gap-1">
          <FieldValue result={result} stale={stale} />
        </div>
      </div>
      <div className="ms-[22px] mt-0.5 grid grid-cols-[minmax(0,1fr)_minmax(0,10rem)_28px_28px] items-center gap-1">
        <BareInput
          value={field.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          placeholder={missing ? t("missingHint") : t("addDescription")}
          aria-label={t("intent")}
          className={cn(
            CELL_INPUT,
            "h-6 text-xs text-ink-3",
            missing && "placeholder:text-warn-ink"
          )}
        />
        <TemplateTypeSelect
          value={field.templateType}
          onChange={(templateType) => onUpdate({ templateType })}
          className="h-6 text-xs"
        />
        <ListToggle
          value={field.templateType}
          onChange={(templateType) => onUpdate({ templateType })}
        />
        <Button
          variant="ghost"
          size="icon-xs"
          className="text-ink-4 hover:text-fail-ink pointer-fine:opacity-0 pointer-fine:group-focus-within:opacity-100 pointer-fine:group-hover:opacity-100"
          onClick={onRemove}
          aria-label={t("removeField", { name: field.name || t("namePlaceholder") })}
        >
          <X />
        </Button>
      </div>
      {duplicate ? (
        <p className="ms-[22px] px-2 text-xs text-fail-ink">{t("duplicateName")}</p>
      ) : null}
      <div className="ms-[22px]">
        <SchemaFieldExtraConfig field={field} onUpdate={onUpdate} />
      </div>
    </motion.li>
  );
}

/** The fields to read from a document: name, value found in the sample, description, type. */
export function SchemaTable({
  schema,
  results,
  staleFields,
  onChange,
}: {
  schema: SchemaField[];
  results?: Map<string, FieldResult>;
  staleFields?: Set<string>;
  onChange: (schema: SchemaField[]) => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const [importOpen, setImportOpen] = useState(false);
  const [addedId, setAddedId] = useState<string | null>(null);
  const duplicates = useMemo(() => {
    const keys = schema.map((field) => fieldKey(field.name)).filter(Boolean);
    return new Set(keys.filter((key, i) => keys.indexOf(key) !== i));
  }, [schema]);
  const update = (id: string, patch: Partial<SchemaField>) =>
    onChange(schema.map((f) => (f.id === id ? { ...f, ...patch } : f)));

  return (
    <div className="flex flex-col">
      <ImportNuextractTemplateDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        hasExistingFields={schema.some((f) => f.name.trim())}
        onImport={(fields, mode) => onChange(mode === "append" ? [...schema, ...fields] : fields)}
      />
      <div className={cn("h-7 border-b border-line px-2 text-xs font-medium text-ink-4", ROW_GRID)}>
        <span />
        <span className="px-2">{t("name")}</span>
        <span className="px-1.5 text-end">{t("valueColumn")}</span>
      </div>
      {schema.length ? (
        <ul className="divide-y divide-line">
          <AnimatePresence initial={false}>
            {schema.map((field) => (
              <SchemaFieldRow
                key={field.id}
                field={field}
                duplicate={duplicates.has(fieldKey(field.name))}
                result={results?.get(fieldKey(field.name))}
                stale={staleFields?.has(field.id) ?? false}
                focusName={field.id === addedId}
                onUpdate={(patch) => update(field.id, patch)}
                onRemove={() => onChange(schema.filter((f) => f.id !== field.id))}
              />
            ))}
          </AnimatePresence>
        </ul>
      ) : (
        <p className="px-4 py-6 text-[13px] text-ink-3">{t("empty")}</p>
      )}
      <div className="flex items-center gap-1 border-t border-line px-1.5 py-1">
        <Button
          variant="ghost"
          size="xs"
          onClick={() => {
            const field = newSchemaField();
            setAddedId(field.id);
            onChange([...schema, field]);
          }}
        >
          <Plus />
          {t("addField")}
        </Button>
        <Button variant="ghost" size="xs" onClick={() => setImportOpen(true)}>
          <FileJson2 />
          {t("importTemplate")}
        </Button>
      </div>
    </div>
  );
}
