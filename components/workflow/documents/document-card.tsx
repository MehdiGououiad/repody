"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DocumentDef } from "@/lib/types";
import type { ProcessingOptions } from "./processing-options";
import { SchemaTable } from "./schema-table";
import { ProcessingSettings } from "./processing-settings";

export function DocumentCard({
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
  const namedFieldNames = doc.schema
    .filter((f) => f.name.trim())
    .map((f) => f.name.trim());

  return (
    <div className="panel-elevated rounded-xl overflow-hidden">
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={onRemove}
        title={tCommon("confirmDelete")}
        description={`${doc.documentType || t("docSource.documentTypePlaceholder")} — ${tCommon("deleteWarning")}`}
      />
      <div className="flex w-full items-center gap-3 px-5 py-4 select-none hover:bg-surface-bright transition-colors">
        <button
          type="button"
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 border-0 bg-transparent p-0 text-left text-on-surface"
          onClick={() => setOpen((v: boolean) => !v)}
          aria-expanded={open}
          aria-controls={`doc-panel-${doc.id}`}
        >
          <div className="size-8 rounded-lg bg-accent-blue/15 ring-1 ring-accent-blue/20 flex items-center justify-center shrink-0">
            <FileText className="h-4 w-4 text-primary" />
          </div>

          <div className="flex-1 min-w-0">
            <span className="text-sm font-semibold">
              {doc.documentType || (
                <span className="text-on-surface-variant font-normal">
                  {t("docSource.unnamedDoc")} {index + 1}
                </span>
              )}
            </span>
            <p className="text-[11px] text-on-surface-variant mt-0.5 truncate">
              {namedFieldNames.length > 0
                ? `${namedFieldNames.length} ${namedFieldNames.length !== 1 ? t("schema.fieldsLabel") : t("schema.fieldLabel")} · ${namedFieldNames.join(", ")}`
                : t("schema.emptyShort")}
            </p>
          </div>

          {open ? (
            <ChevronDown className="h-4 w-4 text-on-surface-variant" />
          ) : (
            <ChevronRight className="h-4 w-4 text-on-surface-variant" />
          )}
        </button>

        {canRemove ? (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-outline hover:text-danger"
            onClick={() => setConfirmOpen(true)}
            aria-label={tCommon("delete")}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        ) : null}
      </div>

      {open ? (
        <div id={`doc-panel-${doc.id}`} className="px-5 pb-5 pt-2 space-y-4 border-t border-border">
          <div className="max-w-sm space-y-1.5">
            <Label htmlFor={`doc-type-${doc.id}`} className="text-xs font-semibold">
              {t("docSource.documentTypeLabel")}
            </Label>
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

          <div className="space-y-1.5">
            <Label htmlFor={`doc-instructions-${doc.id}`} className="text-xs font-semibold">
              {t("docSource.extractionInstructionsLabel")}
            </Label>
            <textarea
              id={`doc-instructions-${doc.id}`}
              name={`document-instructions-${doc.id}`}
              value={doc.extractionInstructions ?? ""}
              onChange={(e) => onChange({ extractionInstructions: e.target.value })}
              placeholder={t("docSource.extractionInstructionsPlaceholder")}
              rows={3}
              className="flex min-h-[72px] w-full rounded-md border border-input bg-card px-3 py-2 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 focus-visible:border-ring"
            />
            <p className="text-[11px] text-on-surface-variant">
              {t("docSource.extractionInstructionsHint")}
            </p>
          </div>

          <SchemaTable
            schema={doc.schema}
            onChange={(schema) => onChange({ schema })}
            t={t}
          />

          <ProcessingSettings
            t={t}
            doc={doc}
            options={processingOptions}
            onChange={onChange}
            onRetry={onRetryProcessingOptions}
          />
        </div>
      ) : null}
    </div>
  );
}
