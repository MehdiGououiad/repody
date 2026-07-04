"use client";

import { useTranslations } from "next-intl";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { REPODY_VLM_CATALOG_ID } from "@/lib/document-model-branding";
import { normalizeReadPath } from "@/lib/api/processing-paths";
import type { DocumentDef } from "@/lib/types";
import type { ProcessingOptions } from "./processing-options";

export function ProcessingSettings({
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
  const { paths, ocrModels, defaultPath, defaultOcr, loaded, error } = options;

  const pathId = normalizeReadPath(doc.extractionMode ?? defaultPath);
  const pathSpec = paths.find((p) => p.id === pathId);
  const showReadPath = paths.length > 1;
  const modelsForPath = ocrModels;
  const firstAvailable = modelsForPath.find((m) => m.available !== false);
  const selectedOcr = doc.ocrModel ?? firstAvailable?.id ?? defaultOcr;
  const selectedModel = modelsForPath.find((m) => m.id === selectedOcr) ?? ocrModels.find((m) => m.id === selectedOcr);
  const markdownOnlyForced = selectedModel?.markdownOnly === true;
  const readPathId = `read-path-${doc.id}`;
  const extractionModelId = `extraction-model-${doc.id}`;

  const runtimeLabel =
    selectedModel?.runtime === "docker_model_runner"
      ? t("extraction.runtimeDirect")
      : (selectedModel?.runtime ?? null);

  const onPathChange = (v: string) => {
    const firstModel = ocrModels.find((m) => m.available !== false);
    onChange({
      extractionMode: v,
      ocrModel: firstModel?.id ?? doc.ocrModel,
    });
  };

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

      {showReadPath ? (
        <div className="space-y-1.5">
          <Label htmlFor={readPathId} className="text-xs font-semibold">
            {t("extraction.readPathLabel")}
          </Label>
          <Select value={pathId} onValueChange={onPathChange} disabled={!loaded || error}>
            <SelectTrigger id={readPathId} className="h-9">
              <SelectValue placeholder={t("extraction.readPathPlaceholder")} />
            </SelectTrigger>
            <SelectContent>
              {paths.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[11px] text-on-surface-variant">
            {pathSpec?.description ?? t("extraction.readPathHintDefault")}
          </p>
        </div>
      ) : null}

      <div className="space-y-1.5">
        <Label htmlFor={extractionModelId} className="text-xs font-semibold">
          {t("extraction.documentModelLabel")}
        </Label>
        <Select
          value={selectedOcr}
          onValueChange={(v) => {
            const model = ocrModels.find((m) => m.id === v);
            const patch: Partial<DocumentDef> = { ocrModel: v };
            if (model?.markdownOnly) {
              patch.markdownExtraction = true;
            }
            onChange(patch);
          }}
          disabled={!loaded || error}
        >
          <SelectTrigger id={extractionModelId} className="h-9">
            <SelectValue placeholder={t("extraction.ocrModelPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {modelsForPath.length === 0 ? (
              <SelectItem value={REPODY_VLM_CATALOG_ID} disabled>
                {t("extraction.ocrModelLoading")}
              </SelectItem>
            ) : (
              modelsForPath.map((m) => (
                <SelectItem key={m.id} value={m.id} disabled={m.available === false}>
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

      <label className="flex items-start gap-2.5 rounded-lg border border-border/70 bg-card/70 px-3 py-2.5 cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 size-4 rounded border-border text-primary focus-visible:ring-2 focus-visible:ring-ring/30"
          checked={markdownOnlyForced ? true : (doc.markdownExtraction ?? false)}
          onChange={(e) => onChange({ markdownExtraction: e.target.checked })}
          disabled={!loaded || error || markdownOnlyForced}
        />
        <span className="min-w-0">
          <span className="block text-xs font-semibold text-on-surface">
            {t("extraction.markdownExtractionLabel")}
          </span>
          <span className="block text-[11px] leading-relaxed text-on-surface-variant mt-0.5">
            {t("extraction.markdownExtractionHint")}
          </span>
        </span>
      </label>
    </div>
  );
}
