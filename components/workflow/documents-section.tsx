"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Plus,
  Trash2,
  GripVertical,
  ChevronDown,
  ChevronRight,
  FileText,
  Sparkles,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn, shortId } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type OcrModelOption } from "@/lib/api/ocr";
import { REPODY_VLM_CATALOG_ID } from "@/lib/document-model-branding";
import {
  normalizeReadPath,
  normalizeValidationMode,
  type ReadPathOption,
  type ValidationModeOption,
} from "@/lib/api/processing-paths";
import { useOcrModelsCatalog, useProcessingPathsCatalog } from "@/lib/hooks/use-catalog-queries";
import { SectionHeading } from "@/components/layout/section-heading";
import type { DocumentDef, ValidationModeId, SchemaField } from "@/lib/types";

export type ProcessingOptions = {
  paths: ReadPathOption[];
  validationModes: ValidationModeOption[];
  ocrModels: OcrModelOption[];
  defaultPath: string;
  defaultValidation: ValidationModeId;
  defaultOcr: string;
  loaded: boolean;
  error: boolean;
};

const EMPTY_PROCESSING_OPTIONS: ProcessingOptions = {
  paths: [],
  validationModes: [],
  ocrModels: [],
  defaultPath: "document_model",
  defaultValidation: "logic_only",
  defaultOcr: REPODY_VLM_CATALOG_ID,
  loaded: false,
  error: false,
};

function SchemaTable({
  schema,
  onChange,
  t,
}: {
  schema: SchemaField[];
  onChange: (schema: SchemaField[]) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const tCommon = useTranslations("common");
  const update = (id: string, patch: Partial<SchemaField>) =>
    onChange(schema.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  const remove = (id: string) => onChange(schema.filter((f) => f.id !== id));
  const add = () =>
    onChange([
      ...schema,
      { id: `f${shortId()}`, name: "", description: "" },
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
          <div className="grid grid-cols-[1fr_2fr_32px] gap-0 bg-surface-container-low border-b border-border">
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant border-r border-border">
              {t("schema.name")}
            </div>
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              {t("schema.intent")}
            </div>
          </div>
          <div className="divide-y divide-border">
            {schema.map((f) => (
              <div
                key={f.id}
                className="grid grid-cols-[1fr_2fr_32px] group hover:bg-surface-bright transition-colors"
              >
                <div className="flex items-center gap-1 px-2 border-r border-border">
                  <GripVertical className="h-3 w-3 text-outline-variant opacity-0 group-hover:opacity-60 cursor-grab shrink-0" />
                  <Input
                    value={f.name}
                    onChange={(e) => update(f.id, { name: e.target.value })}
                    placeholder={t("schema.namePlaceholder")}
                    className="font-mono text-xs h-9 border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input"
                  />
                </div>
                <div className="px-2 flex items-center">
                  <Input
                    value={f.description}
                    onChange={(e) => update(f.id, { description: e.target.value })}
                    placeholder={t("schema.descriptionPlaceholder")}
                    className="text-xs h-9 border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input"
                  />
                </div>
                <div className="flex items-center justify-center">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-outline hover:text-danger opacity-0 group-hover:opacity-100"
                    onClick={() => remove(f.id)}
                    aria-label={tCommon("delete")}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ProcessingSettings({
  doc,
  onChange,
  t,
  options,
  onRetry,
}: {
  doc: DocumentDef;
  onChange: (patch: Partial<DocumentDef>) => void;
  t: ReturnType<typeof useTranslations>;
  options: ProcessingOptions;
  onRetry: () => void;
}) {
  const {
    paths,
    validationModes,
    ocrModels,
    defaultPath,
    defaultOcr,
    loaded,
    error,
  } = options;

  const pathId = normalizeReadPath(doc.extractionMode ?? defaultPath);
  const pathSpec = paths.find((p) => p.id === pathId);
  const validationId = normalizeValidationMode(doc.validationMode, doc.extractionMode);
  const validationSpec = validationModes.find((v) => v.id === validationId);
  const documentModels = ocrModels.filter((m) => m.engine === "document_model");
  const firstAvailable = documentModels.find((m) => m.available !== false);
  const selectedOcr = doc.ocrModel ?? firstAvailable?.id ?? defaultOcr;
  const selectedModel = documentModels.find((m) => m.id === selectedOcr);
  const readPathId = `read-path-${doc.id}`;
  const validationModeId = `validation-mode-${doc.id}`;
  const extractionModelId = `extraction-model-${doc.id}`;
  const validationHint =
    validationSpec?.description ?? t("extraction.directModelLogicValidationHint");

  const runtimeLabel = selectedModel?.runtime === "docker_model_runner"
    ? t("extraction.runtimeDirect")
    : selectedModel?.runtime ?? null;

  const onPathChange = (v: string) => {
    const firstModel = ocrModels.find((m) => m.available !== false);
    onChange({
      extractionMode: v,
      ocrModel: firstModel?.id ?? doc.ocrModel,
    });
  };

  const onValidationChange = (v: string) => {
    onChange({ validationMode: v as ValidationModeId });
  };

  return (
    <div className="space-y-3 rounded-lg border border-border bg-surface-container-low/50 p-4">
      {error ? (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger/5 p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-danger">
              {t("extraction.configurationUnavailable")}
            </p>
            <p className="mt-0.5 text-[11px] text-danger-strong">
              {t("extraction.configurationUnavailableHint")}
            </p>
          </div>
          <Button variant="outline" size="sm" className="h-7 gap-1 text-[11px]" onClick={onRetry}>
            <RefreshCw className="h-3 w-3" />
            {t("extraction.retry")}
          </Button>
        </div>
      ) : null}

      <div className="space-y-1.5">
        <Label htmlFor={readPathId} className="text-xs font-semibold">
          {t("extraction.readPathLabel")}
        </Label>
        <Select value={pathId} onValueChange={onPathChange} disabled={!loaded || error}>
          <SelectTrigger id={readPathId} className="h-9">
            <SelectValue placeholder={t("extraction.readPathPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {paths.length === 0 ? (
              <SelectItem value="document_model" disabled>
                {t("extraction.pathLoading")}
              </SelectItem>
            ) : (
              paths.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.label}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
        <p className="text-[11px] text-on-surface-variant">
          {pathSpec?.description ?? t("extraction.readPathHintDefault")}
        </p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={validationModeId} className="text-xs font-semibold">
          {t("extraction.validationModeLabel")}
        </Label>
        <Select value={validationId} onValueChange={onValidationChange} disabled={!loaded || error}>
          <SelectTrigger id={validationModeId} className="h-9">
            <SelectValue placeholder={t("extraction.validationModePlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {validationModes.length === 0 ? (
              <SelectItem value="logic_only" disabled>
                {t("extraction.pathLoading")}
              </SelectItem>
            ) : (
              validationModes.map((v) => (
                <SelectItem key={v.id} value={v.id}>
                  {v.label}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
        <p className="text-[11px] text-on-surface-variant">
          {validationHint}
        </p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={extractionModelId} className="text-xs font-semibold">
          {t("extraction.documentModelLabel")}
        </Label>
        <Select
          value={selectedOcr}
          onValueChange={(v) => onChange({ ocrModel: v })}
          disabled={!loaded || error}
        >
          <SelectTrigger id={extractionModelId} className="h-9">
            <SelectValue placeholder={t("extraction.ocrModelPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {documentModels.length === 0 ? (
              <SelectItem value={REPODY_VLM_CATALOG_ID} disabled>
                {t("extraction.ocrModelLoading")}
              </SelectItem>
            ) : (
              documentModels.map((m) => (
                <SelectItem
                  key={m.id}
                  value={m.id}
                  disabled={m.available === false}
                >
                  {m.available === false
                    ? `${m.label} — ${t("extraction.unavailable")}`
                    : m.label}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
        {selectedModel?.description ? (
          <div className="rounded-lg border border-border/70 bg-card/70 px-3 py-2">
            <div className="mb-1 flex items-center gap-2">
              {runtimeLabel ? (
                <Badge variant="info" className="text-[9px]">
                  {runtimeLabel}
                </Badge>
              ) : null}
            </div>
            <p className="text-[11px] leading-relaxed text-on-surface-variant">
                {selectedModel.description}
                {selectedModel.available === false && selectedModel.availabilityNote
                  ? ` ${selectedModel.availabilityNote}`
                  : ""}
              </p>
            </div>
          ) : null}
      </div>
    </div>
  );
}

function DocumentCard({
  doc,
  index,
  canRemove,
  onChange,
  onRemove,
  processingOptions,
  onRetryProcessingOptions,
}: {
  doc: DocumentDef;
  index: number;
  canRemove: boolean;
  onChange: (patch: Partial<DocumentDef>) => void;
  onRemove: () => void;
  processingOptions: ProcessingOptions;
  onRetryProcessingOptions: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const [open, setOpen] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const fieldCount = doc.schema.length;

  return (
    <div className="panel-elevated rounded-xl overflow-hidden">
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={onRemove}
        title={tCommon("confirmDelete")}
        description={`${doc.documentType || t("docSource.documentTypePlaceholder")} — ${tCommon("deleteWarning")}`}
      />
      <button
        type="button"
        className="flex w-full items-center gap-3 px-5 py-4 cursor-pointer select-none hover:bg-surface-bright transition-colors text-left"
        onClick={() => setOpen((v: boolean) => !v)}
        aria-expanded={open}
        aria-controls={`doc-panel-${doc.id}`}
      >
        <div className="size-8 rounded-lg bg-accent-blue/15 ring-1 ring-accent-blue/20 flex items-center justify-center shrink-0">
          <FileText className="h-4 w-4 text-primary" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold">
              {doc.documentType || (
                <span className="text-on-surface-variant font-normal">{t("docSource.documentTypePlaceholder")}</span>
              )}
            </span>
            <Badge variant="outline" className="text-[10px] font-normal">
              {t("docSource.docLabel")} {index + 1}
            </Badge>
          </div>
          <p className="text-[11px] text-on-surface-variant mt-0.5">
            {fieldCount > 0
              ? doc.schema.filter((f) => f.name).map((f) => f.name).join(", ")
              : t("schema.empty")}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {canRemove ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-outline hover:text-danger"
              onClick={(e) => { e.stopPropagation(); setConfirmOpen(true); }}
              aria-label={tCommon("delete")}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          ) : null}
          {open
            ? <ChevronDown className="h-4 w-4 text-on-surface-variant" />
            : <ChevronRight className="h-4 w-4 text-on-surface-variant" />}
        </div>
      </button>

      {open ? (
        <div id={`doc-panel-${doc.id}`} className="px-5 pb-5 pt-2 space-y-4 border-t border-border">
          <div className="max-w-sm space-y-1.5">
            <Label htmlFor={`doc-type-${doc.id}`} className="text-xs font-semibold">{t("docSource.documentTypeLabel")}</Label>
            <Input
              id={`doc-type-${doc.id}`}
              name={`document-type-${doc.id}`}
              autoComplete="off"
              value={doc.documentType}
              onChange={(e) => onChange({ documentType: e.target.value })}
              placeholder={t("docSource.documentTypePlaceholder")}
              className="h-9"
            />
            <p className="text-[11px] text-on-surface-variant">{t("docSource.documentTypeHint")}</p>
          </div>

          <SchemaTable
            schema={doc.schema}
            onChange={(schema) => onChange({ schema })}
            t={t}
          />

          <ProcessingSettings
            doc={doc}
            onChange={onChange}
            t={t}
            options={processingOptions}
            onRetry={onRetryProcessingOptions}
          />
        </div>
      ) : null}
    </div>
  );
}

export function DocumentsSection({
  documents,
  onChange,
}: {
  documents: DocumentDef[];
  onChange: (docs: DocumentDef[]) => void;
}) {
  const t = useTranslations("workflows.builder");
  const pathsQuery = useProcessingPathsCatalog();
  const ocrQuery = useOcrModelsCatalog();

  const processingOptions = useMemo((): ProcessingOptions => {
    const loaded = pathsQuery.isFetched && ocrQuery.isFetched;
    const error = pathsQuery.isError || ocrQuery.isError;
    if (!pathsQuery.data || !ocrQuery.data) {
      return { ...EMPTY_PROCESSING_OPTIONS, loaded, error };
    }
    return {
      paths: pathsQuery.data.paths,
      validationModes: pathsQuery.data.validationModes,
      defaultPath: pathsQuery.data.defaultPath,
      defaultValidation:
        (pathsQuery.data.defaultValidationMode as ValidationModeId) || "logic_only",
      ocrModels: ocrQuery.data.models,
      defaultOcr: ocrQuery.data.defaultModel,
      loaded: true,
      error: false,
    };
  }, [
    pathsQuery.data,
    pathsQuery.isFetched,
    pathsQuery.isError,
    ocrQuery.data,
    ocrQuery.isFetched,
    ocrQuery.isError,
  ]);

  const retryProcessingOptions = () => {
    void pathsQuery.refetch();
    void ocrQuery.refetch();
  };

  const updateDoc = (id: string, patch: Partial<DocumentDef>) =>
    onChange(documents.map((d) => (d.id === id ? { ...d, ...patch } : d)));
  const removeDoc = (id: string) => onChange(documents.filter((d) => d.id !== id));
  const addDoc = () =>
    onChange([
      ...documents,
      {
        id: `doc${shortId()}`,
        documentType: "",
        schema: [],
        extractionMode: "document_model",
        validationMode: "logic_only",
        ocrModel: REPODY_VLM_CATALOG_ID,
      },
    ]);

  return (
    <div className="space-y-4">
      <SectionHeading title={t("docSource.title")} description={t("docSource.hint")} eyebrow="Schema" />

      <div className="space-y-3">
        {documents.map((doc, i) => (
          <DocumentCard
            key={doc.id}
            doc={doc}
            index={i}
            canRemove={documents.length > 1}
            onChange={(patch) => updateDoc(doc.id, patch)}
            onRemove={() => removeDoc(doc.id)}
            processingOptions={processingOptions}
            onRetryProcessingOptions={retryProcessingOptions}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={addDoc}
        className={cn(
          "w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 border-dashed border-accent-blue/30",
          "text-sm text-on-surface-variant hover:border-accent-blue/60 hover:text-on-surface hover:bg-accent-blue/5 transition-[border-color,color,background-color]"
        )}
      >
        <Plus className="h-4 w-4" />
        {t("docSource.addDocument")}
      </button>
    </div>
  );
}
