"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { DocChip } from "@/components/shared/doc-chip";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import type { RunAuditDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

/** One page, fading in once loaded; its frame keeps an A4 shape meanwhile. */
function PageImage({ src, label }: { src: string; label: string }) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const t = useTranslations("audits.report");
  return (
    <figure className="flex flex-col gap-1.5">
      <div
        className={cn(
          "relative overflow-hidden rounded-md bg-panel shadow-[0_0_0_1px_var(--line),0_8px_24px_-12px_var(--shadow-color)]",
          !loaded && "aspect-[1/1.414] animate-pulse bg-selected [animation-duration:1.6s]",
        )}
      >
        {failed ? (
          <p className="absolute inset-0 flex items-center justify-center text-xs text-ink-4">
            {t("noPreview")}
          </p>
        ) : (
          // oxlint-disable-next-line nextjs/no-img-element -- pages come from the API as rendered WebP.
          <img
            src={src}
            alt={label}
            loading="lazy"
            decoding="async"
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
            className={cn(
              "block h-auto w-full transition-opacity duration-300",
              loaded ? "opacity-100" : "opacity-0",
            )}
          />
        )}
      </div>
      <figcaption className="text-center text-2xs tabular-nums text-ink-4">{label}</figcaption>
    </figure>
  );
}

/** The run's documents, page by page, one tab per document in its colour. */
export function DocumentViewer({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  const docs = audit.documents;
  if (!docs.length) return null;
  return (
    <Tabs defaultValue={docs[0].id} className="flex h-full min-h-0 flex-col">
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-line px-3">
        <TabsList aria-label={t("extractedData")} className="min-w-0 overflow-x-auto">
          {docs.map((doc, index) => (
            <TabsTab key={doc.id} value={doc.id} className="max-w-56">
              <DocChip index={index}>{doc.documentType}</DocChip>
            </TabsTab>
          ))}
        </TabsList>
      </div>
      {docs.map((doc) => {
        const pages = Math.max(doc.extraction?.pagesRendered ?? 1, 1);
        return (
          <TabsPanel
            key={doc.id}
            value={doc.id}
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-canvas p-4"
          >
            <p className="mb-3 truncate text-xs text-ink-3">
              {doc.fileName} · {t("pages", { count: pages })}
            </p>
            <div className="mx-auto flex max-w-[720px] flex-col gap-4">
              {Array.from({ length: pages }, (_, i) => i + 1).map((page) => (
                <PageImage
                  key={page}
                  src={`/api/v1/runs/${encodeURIComponent(audit.id)}/documents/${encodeURIComponent(doc.id)}/pages/${page}`}
                  label={t("page", { page })}
                />
              ))}
            </div>
          </TabsPanel>
        );
      })}
    </Tabs>
  );
}
