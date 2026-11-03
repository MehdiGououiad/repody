"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import type { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { REPODY_VLM_LABEL } from "@/lib/document-model-branding";
import type { DocumentDef } from "@/lib/types";

import type { ProcessingOptions } from "./processing-options";

/** The document model is fixed (NuExtract via Repody VLM); show it and its live availability. */
export function ProcessingSettings({
  t,
  options,
  onRetry,
}: {
  t: ReturnType<typeof useTranslations>;
  doc: DocumentDef;
  options: ProcessingOptions;
  onChange: (patch: Partial<DocumentDef>) => void;
  onRetry: () => void;
}) {
  const { error, loaded, documentModelIds } = options;
  const model = documentModelIds[0];
  const offline = loaded && model?.available === false;

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

      <div className="max-w-lg space-y-1.5">
        <p className="text-xs font-semibold">{t("extraction.documentModelLabel")}</p>
        <div className="flex items-center gap-2 text-sm">
          <span>{REPODY_VLM_LABEL}</span>
          {offline ? (
            <Badge variant="danger" className="text-[10px]">
              {t("extraction.offlineBadge")}
            </Badge>
          ) : null}
        </div>
        <p className="text-[11px] leading-relaxed text-on-surface-variant">
          {offline && model?.availabilityNote
            ? model.availabilityNote
            : t("extraction.profileNuextractQ4Hint")}
        </p>
      </div>
    </div>
  );
}
