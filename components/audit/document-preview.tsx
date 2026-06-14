"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ZoomIn, ZoomOut, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCrossHighlight } from "@/lib/stores/cross-highlight";
import { cn } from "@/lib/utils";
import type { AuditDetail, ExtractedField } from "@/lib/types";

const PREVIEW_WIDTH = 560;
const PREVIEW_HEIGHT = 792;

export function DocumentPreview({ audit }: { audit: AuditDetail }) {
  const t = useTranslations("audits.detail.panels");
  const tCommon = useTranslations("common");
  const { hoveredFieldKey, selectedRuleId, setHoveredField } = useCrossHighlight();
  const [zoom, setZoom] = useState(1);

  const failedKeysForSelectedRule = useMemo(() => {
    if (!selectedRuleId) return new Set<string>();
    const rule = audit.rules.find((r) => r.id === selectedRuleId);
    return new Set(rule?.affectedFieldKeys ?? []);
  }, [selectedRuleId, audit.rules]);

  const fieldsWithBbox = audit.extractedFields.filter(
    (f): f is ExtractedField & { bbox: NonNullable<ExtractedField["bbox"]> } => Boolean(f.bbox)
  );

  return (
    <div className="flex flex-col h-full bg-card">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-container-low shrink-0">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-on-surface-variant" aria-hidden="true" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("document")}
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label={tCommon("zoomOut")}
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
            disabled={zoom <= 0.5}
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label={tCommon("zoomIn")}
            onClick={() => setZoom((z) => Math.min(2, z + 0.25))}
            disabled={zoom >= 2}
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-surface-container-low">
        <div
          className="relative mx-auto origin-top"
          style={{
            width: PREVIEW_WIDTH * zoom,
            maxWidth: "100%",
          }}
        >
          <div
            className="relative bg-white rounded-md shadow-sm util-border"
            style={{
              width: PREVIEW_WIDTH,
              transform: `scale(${zoom})`,
              transformOrigin: "top center",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={audit.documentUrl}
              alt={`${audit.workflowName} — ${audit.entity}`}
              width={PREVIEW_WIDTH}
              height={PREVIEW_HEIGHT}
              className="w-full h-auto block rounded-md"
            />
            {fieldsWithBbox.map((f) => {
              const isHovered = hoveredFieldKey === f.key;
              const isFailedForSelectedRule = failedKeysForSelectedRule.has(f.key);
              const isFailingField = (f.failedRuleIds?.length ?? 0) > 0;
              return (
                <button
                  type="button"
                  key={f.key}
                  onMouseEnter={() => setHoveredField(f.key)}
                  onMouseLeave={() => setHoveredField(null)}
                  onFocus={() => setHoveredField(f.key)}
                  onBlur={() => setHoveredField(null)}
                  aria-label={`${f.key}: ${f.value}`}
                  aria-pressed={isHovered}
                  className={cn(
                    "absolute border rounded-sm transition-[border-color,background-color,box-shadow] cursor-pointer pointer-events-auto",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-1",
                    isFailedForSelectedRule
                      ? "border-danger bg-danger/20 ring-2 ring-danger/40"
                      : isFailingField
                        ? "border-danger/60 bg-danger/10"
                        : "border-accent-blue/40 bg-accent-blue/5 hover:bg-accent-blue/15",
                    isHovered && "ring-2 ring-accent-blue"
                  )}
                  style={{
                    left: `${f.bbox.x}%`,
                    top: `${f.bbox.y}%`,
                    width: `${f.bbox.w}%`,
                    height: `${f.bbox.h}%`,
                  }}
                  title={`${f.key}: ${f.value}`}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
