"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { $api } from "@/lib/api/browser";

/** The document model is set by the platform (NuExtract on llama-server): show which one, and
 * whether it is being served. */
export function ProcessingSettings() {
  const t = useTranslations("workflows.builder");
  const config = $api.useQuery("get", "/v1/platform/config");
  // null: not probed (an endpoint that scales to zero starts on the first run).
  const offline = config.isSuccess && config.data.modelAvailable === false;

  return (
    <div className="space-y-3 rounded-lg border border-line bg-raised/50 p-4">
      {config.isError ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-fail/30 bg-fail/5 p-3"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-fail-ink" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-fail-ink">
              {t("extraction.configurationUnavailable")}
            </p>
            <p className="mt-0.5 text-2xs text-fail-ink">
              {t("extraction.configurationUnavailableHint")}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1 text-2xs"
            onClick={() => void config.refetch()}
          >
            <RefreshCw className="h-3 w-3" />
            {t("extraction.retry")}
          </Button>
        </div>
      ) : null}

      <div className="max-w-lg space-y-1.5">
        <p className="text-xs font-semibold">{t("extraction.documentModelLabel")}</p>
        <div className="flex items-center gap-2 text-sm">
          <span className="font-mono">{config.data?.servedModel ?? "…"}</span>
          {offline ? (
            <Badge variant="danger" className="text-2xs">
              {t("extraction.offlineBadge")}
            </Badge>
          ) : null}
        </div>
        <p className="text-2xs leading-relaxed text-ink-3">
          {t("extraction.profileNuextractQ4Hint")}
        </p>
      </div>
    </div>
  );
}
