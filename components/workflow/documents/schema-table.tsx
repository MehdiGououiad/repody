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

export type FieldResult = { extracted: boolean; value: unknown };

const ROW_BASE = "grid grid-cols-[minmax(0,1fr)_9.5rem_28px_24px] items-center gap-x-1.5";
const ROW_WITH_RESULTS =
  "grid grid-cols-[14px_minmax(0,1fr)_9rem_28px_minmax(0,0.9fr)_24px] items-center gap-x-1.5";

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
              : "animate-[wash-warn_0.8s_ease-out]"),
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
  showResults,
  result,
  stale,
  focusName,
  onUpdate,
  onRemove,
}: {
  field: SchemaField;
  duplicate: boolean;
  showResults: boolean;
  focusName: boolean;
  result: FieldResult | undefined;
  stale: boolean;
  onUpdate: (patch: Partial<SchemaField>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const missing = Boolean(result && !result.extracted && !stale);
  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, transition: { duration: 0.12 } }}
      transition={{ duration: 0.18, ease: EASE_OUT }}
      className={cn("group relative px-2 py-1.5", missing && "bg-warn-wash/40")}
    >
      <div className={showResults ? ROW_WITH_RESULTS : ROW_BASE}>
        {showResults ? (
          <StatusGlyph
            status={!result || stale ? "waiting" : result.extracted ? "passed" : "warning"}
            className="justify-self-center"
          />
        ) : null}
        <BareInput
          value={field.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
          placeholder={t("namePlaceholder")}
          aria-label={t("name")}
          // oxlint-disable-next-line jsx-a11y/no-autofocus -- a field just added is named first.
          autoFocus={focusName}
          aria-invalid={duplicate}
          className={cn(CELL_INPUT, "font-medium", duplicate && "text-fail-ink")}
        />
        <TemplateTypeSelect
          value={field.templateType}
          onChange={(templateType) => onUpdate({ templateType })}
          className="h-7 text-xs"
        />
        <ListToggle
          value={field.templateType}
          onChange={(templateType) => onUpdate({ templateType })}
        />
        {showResults ? (
          <div className="flex min-w-0 items-center justify-end">
            <FieldValue result={result} stale={stale} />
          </div>
        ) : null}
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
      <div className={cn("mt-0.5 pe-7", showResults && "ms-[20px]")}>
        <BareInput
          value={field.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          placeholder={missing ? t("missingHint") : t("addDescription")}
          aria-label={t("intent")}
          className={cn(
            CELL_INPUT,
            "h-6 text-xs text-ink-3",
            missing && "placeholder:text-warn-ink",
          )}
        />
        {duplicate ? <p className="px-2 text-xs text-fail-ink">{t("duplicateName")}</p> : null}
        <SchemaFieldExtraConfig field={field} onUpdate={onUpdate} />
      </div>
    </motion.li>
  );
}

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
  const showResults = results !== undefined;
  const duplicates = useMemo(() => {
    const keys = schema.map((field) => fieldKey(field.name)).filter(Boolean);
    return new Set(keys.filter((key, i) => keys.indexOf(key) !== i));
  }, [schema]);
  const addField = () => {
    const field = newSchemaField();
    setAddedId(field.id);
    onChange([...schema, field]);
  };
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
      <div
        className={cn(
          "h-7 border-b border-line px-2 text-xs font-medium text-ink-4",
          showResults ? ROW_WITH_RESULTS : ROW_BASE,
        )}
      >
        {showResults ? <span /> : null}
        <span className="px-2">{t("name")}</span>
        <span className="px-2">{t("type")}</span>
        <span />
        {showResults ? <span className="px-1.5 text-end">{t("valueColumn")}</span> : null}
        <span />
      </div>
      {schema.length ? (
        <ul className="divide-y divide-line">
          <AnimatePresence initial={false}>
            {schema.map((field) => (
              <SchemaFieldRow
                key={field.id}
                field={field}
                duplicate={duplicates.has(fieldKey(field.name))}
                showResults={showResults}
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
        <button
          type="button"
          onClick={addField}
          className="m-3 flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed border-line-strong px-4 py-8 text-center outline-none transition-colors duration-150 hover:border-accent hover:bg-accent-wash/40 focus-visible:shadow-[0_0_0_2px_var(--focus)]"
        >
          <span className="flex size-8 items-center justify-center rounded-full bg-accent-wash text-accent-ink">
            <Plus className="size-4" aria-hidden />
          </span>
          <span className="text-[13px] font-medium text-ink">{t("addFirstField")}</span>
          <span className="max-w-xs text-xs text-ink-3">{t("empty")}</span>
        </button>
      )}
      <div className="flex items-center gap-1 border-t border-line px-1.5 py-1">
        <Button variant="ghost" size="xs" onClick={addField}>
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
