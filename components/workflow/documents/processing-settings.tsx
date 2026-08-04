"use client";

import { useTranslations } from "next-intl";

import { AlertCircle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  GLM_OCR_CATALOG_ID,
  PADDLEOCR_QWEN_CATALOG_ID,
  PADDLEOCR_V6_CATALOG_ID,
  REPODY_VLM_CATALOG_ID,
  isMarkdownOnlyCatalogId,
  publicDocumentModelLabel,
} from "@/lib/document-model-branding";
import type { DocumentDef } from "@/lib/types";

import type { ProcessingOptions } from "./processing-options";

export function ProcessingSettings({
  t,
  doc,
  options,
  onChange,
  onRetry,
}: {
  t: ReturnType<typeof useTranslations>;
  doc: DocumentDef;
  options: ProcessingOptions;
  onChange: (patch: Partial<DocumentDef>) => void;
  onRetry: () => void;
}) {
  const { error, loaded, documentModelIds, defaultDocumentModel } = options;
  const selected =
    doc.documentModelId?.trim() ||
    defaultDocumentModel ||
    REPODY_VLM_CATALOG_ID;

  const modelHint =
    selected === GLM_OCR_CATALOG_ID
      ? t("extraction.profileGlmOcrHint")
      : selected === PADDLEOCR_V6_CATALOG_ID
        ? t("extraction.profilePaddleocrV6Hint")
        : selected === PADDLEOCR_QWEN_CATALOG_ID
          ? t("extraction.profilePaddleocrQwenHint")
          : t("extraction.profileNuextractQ4Hint");

  return (
    <div className="space-y-3 rounded-lg border border-border bg-surface-container-low/50 p-4">
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger/5 p-3"
        >
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

      <div className="max-w-sm space-y-1.5">
        <Label htmlFor={`extraction-model-${doc.id}`} className="text-xs font-semibold">
          {t("extraction.documentModelLabel")}
        </Label>
        <Select
          value={selected}
          disabled={!loaded || documentModelIds.length === 0}
          onValueChange={(value) => {
            const entry = documentModelIds.find((model) => model.id === value);
            const nextMarkdownOnly =
              entry?.markdownOnly === true || isMarkdownOnlyCatalogId(value);
            onChange({
              documentModelId: value,
              extractionMode: "document_model",
              // Markdown-only catalog models (e.g. PP-OCRv6) always run document→markdown.
              markdownExtraction: nextMarkdownOnly ? true : doc.markdownExtraction,
              ...(nextMarkdownOnly ? { schema: [] } : {}),
            });
          }}
        >
          <SelectTrigger id={`extraction-model-${doc.id}`} className="h-9">
            <SelectValue
              placeholder={
                loaded
                  ? t("extraction.documentModelIdPlaceholder")
                  : t("extraction.documentModelIdLoading")
              }
            />
          </SelectTrigger>
          <SelectContent>
            {documentModelIds.map((model) => (
              <SelectItem
                key={model.id}
                value={model.id}
                disabled={model.available === false}
              >
                {publicDocumentModelLabel(model.id)}
                {model.markdownOnly ? ` · ${t("extraction.markdownOnlyBadge")}` : ""}
                {model.id === defaultDocumentModel ? ` · ${t("extraction.defaultBadge")}` : ""}
                {model.available === false ? ` · ${t("extraction.offlineBadge")}` : ""}
              </SelectItem>
            ))}
            {documentModelIds.length === 0 ? (
              <SelectItem value={REPODY_VLM_CATALOG_ID}>
                {publicDocumentModelLabel(REPODY_VLM_CATALOG_ID)}
              </SelectItem>
            ) : null}
          </SelectContent>
        </Select>
        <p className="text-[11px] leading-relaxed text-on-surface-variant">
          {modelHint}
        </p>
      </div>
    </div>
  );
}
