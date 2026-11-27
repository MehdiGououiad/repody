"use client";

import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
import { TransformComponent, TransformWrapper } from "react-zoom-pan-pinch";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { artifactImageUrl, normalizeBboxToPercent } from "./helpers";
import type { ArtifactRef, FraudFinding } from "./types";

type ViewerProps = {
  analysisId: string | null;
  previewUrl: string | null;
  artifacts: readonly ArtifactRef[];
  findings: readonly FraudFinding[];
  selectedFinding: FraudFinding | null;
  onSelectFinding: (finding: FraudFinding) => void;
};

export function ForensicViewer({
  analysisId,
  previewUrl,
  artifacts,
  findings,
  selectedFinding,
  onSelectFinding,
}: ViewerProps) {
  const t = useTranslations("fraud");
  const [opacity, setOpacity] = useState(75);
  const [showBoxes, setShowBoxes] = useState(true);

  const heatmaps = artifacts.filter((a) => a.kind === "forensic_heatmap");
  const diffs = artifacts.filter((a) => a.kind === "pdf_revision_diff");
  const activeEvidenceId =
    selectedFinding?.evidence_artifact_id ??
    heatmaps[0]?.artifact_id ??
    diffs[0]?.artifact_id ??
    null;

  const evidenceUrl =
    analysisId && activeEvidenceId ? artifactImageUrl(analysisId, activeEvidenceId) : null;
  const diffUrl =
    analysisId && diffs[0] ? artifactImageUrl(analysisId, diffs[0].artifact_id) : evidenceUrl;
  const baseImage = previewUrl ?? evidenceUrl;

  if (!baseImage && !diffUrl) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-xl border border-dashed border-line bg-canvas/50 p-6 text-center text-[13px] text-ink-3">
        {t("viewerEmpty")}
      </div>
    );
  }

  const bboxFindings = findings.filter((f) => Boolean(f.bbox));

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line bg-raised p-3 shadow-panel">
      <Tabs
        defaultValue={
          diffs.length > 0 && selectedFinding?.code === "PDF_REVISION_VISUAL_CHANGE"
            ? "diff"
            : "heatmap"
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2.5">
          <TabsList variant="segmented">
            <TabsTab value="heatmap">{t("tabHeatmap")}</TabsTab>
            <TabsTab value="diff" disabled={!diffUrl}>
              {t("tabRevisionDiff")}
            </TabsTab>
          </TabsList>

          <div className="flex flex-wrap items-center gap-3 text-xs text-ink-2">
            {evidenceUrl ? (
              <label htmlFor="fraud-overlay-opacity" className="flex items-center gap-2">
                <span>{t("overlayOpacity")}</span>
                <input
                  id="fraud-overlay-opacity"
                  type="range"
                  min={0}
                  max={100}
                  value={opacity}
                  onChange={(e) => setOpacity(Number(e.target.value))}
                  className="h-1.5 w-24 accent-[var(--accent)]"
                />
                <span className="w-8 tabular-nums text-ink-3">{opacity}%</span>
              </label>
            ) : null}
            {bboxFindings.length > 0 ? (
              <Button
                variant={showBoxes ? "secondary" : "ghost"}
                size="xs"
                onClick={() => setShowBoxes((v) => !v)}
              >
                {showBoxes ? t("hideBoxes") : t("showBoxes")}
              </Button>
            ) : null}
          </div>
        </div>

        <TabsPanel value="heatmap" className="pt-3">
          <TransformWrapper initialScale={1} minScale={0.5} maxScale={6} centerOnInit>
            {({ zoomIn, zoomOut, resetTransform }) => (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => zoomIn()}
                    aria-label={t("zoomIn")}
                  >
                    <ZoomIn />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => zoomOut()}
                    aria-label={t("zoomOut")}
                  >
                    <ZoomOut />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => resetTransform()}
                    aria-label={t("resetZoom")}
                  >
                    <RotateCcw />
                  </Button>
                </div>

                <div className="relative flex min-h-[380px] items-center justify-center overflow-hidden rounded-lg bg-canvas">
                  <TransformComponent wrapperStyle={{ width: "100%", maxHeight: "560px" }}>
                    <div className="relative inline-block">
                      {baseImage ? (
                        // oxlint-disable-next-line nextjs/no-img-element -- dynamic user upload blob / API evidence stream
                        <img
                          src={baseImage}
                          alt={t("documentAlt")}
                          className="block max-h-[540px] w-auto select-none object-contain"
                        />
                      ) : null}
                      {evidenceUrl && baseImage !== evidenceUrl ? (
                        // oxlint-disable-next-line nextjs/no-img-element -- dynamic API heatmap stream
                        <img
                          src={evidenceUrl}
                          alt={t("heatmapAlt")}
                          style={{ opacity: opacity / 100 }}
                          className="pointer-events-none absolute inset-0 size-full object-contain"
                        />
                      ) : null}
                      {showBoxes
                        ? bboxFindings.map((item) => {
                            if (!item.bbox) return null;
                            const boxStyle = normalizeBboxToPercent(item.bbox);
                            const isSelected = selectedFinding === item;
                            return (
                              <button
                                key={`${item.code}-${item.page ?? 0}-${boxStyle.left}-${boxStyle.top}`}
                                type="button"
                                onClick={() => onSelectFinding(item)}
                                aria-label={`${item.code}: ${item.title}`}
                                title={`${item.code}: ${item.title}`}
                                style={boxStyle}
                                className={cn(
                                  "absolute cursor-pointer rounded-sm border-2 transition-colors",
                                  isSelected
                                    ? "border-accent bg-accent/15 shadow-[0_0_0_2px_var(--focus)]"
                                    : "border-fail bg-fail/10 hover:bg-fail/20",
                                )}
                              />
                            );
                          })
                        : null}
                    </div>
                  </TransformComponent>
                </div>
              </div>
            )}
          </TransformWrapper>
        </TabsPanel>

        <TabsPanel value="diff" className="pt-3">
          {diffUrl ? (
            <div className="overflow-hidden rounded-lg border border-line bg-canvas">
              {previewUrl && previewUrl !== diffUrl ? (
                <ReactCompareSlider
                  itemOne={<ReactCompareSliderImage src={previewUrl} alt={t("documentAlt")} />}
                  itemTwo={<ReactCompareSliderImage src={diffUrl} alt={t("diffAlt")} />}
                  className="max-h-[540px]"
                />
              ) : (
                // oxlint-disable-next-line nextjs/no-img-element -- composite side-by-side PDF revision PNG emitted by repody-fraud
                <img
                  src={diffUrl}
                  alt={t("diffAlt")}
                  className="mx-auto block max-h-[540px] w-auto object-contain"
                />
              )}
            </div>
          ) : null}
        </TabsPanel>
      </Tabs>
    </div>
  );
}
