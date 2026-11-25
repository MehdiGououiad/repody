"use client";

import { Resizable, ResizableHandle, ResizablePanel } from "@ui-sdk/react/resizable";
import { useShortcut } from "@ui-sdk/react/shortcuts";
import { Download, Printer } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { DocumentViewer } from "@/components/audit/document-viewer";
import { ReportBody, ReportVerdict, TimingBar } from "@/components/audit/report";
import { Crumb, Page } from "@/components/layout/page";
import { CopyIconButton } from "@/components/shared/copyable-output-panel";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { useMediaQuery } from "@/lib/hooks/use-media-query";
import type { RunAuditDetail } from "@/lib/types";

/** One finished run: the documents beside the verdict, rules and fields (above them on narrow screens). */
export function RunAuditReport({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  const tNav = useTranslations("nav");
  const router = useRouter();
  const wide = useMediaQuery("(min-width: 1024px)");
  useShortcut("escape", () => router.push("/audits"), { description: tNav("audits") });

  const report = (
    <div className="flex flex-col gap-6 px-5 py-5 md:px-6">
      <div className="flex flex-col gap-4 rounded-xl bg-panel p-5 shadow-panel">
        <ReportVerdict audit={audit} />
        <div className="flex items-center gap-1 ps-8">
          <code className="font-mono text-xs text-ink-4">{audit.id}</code>
          <CopyIconButton
            text={audit.id}
            label={t("copyId")}
            copiedLabel={t("copied")}
            failedLabel={t("copyId")}
          />
        </div>
        <div className="ps-8">
          <TimingBar audit={audit} />
        </div>
      </div>
      <ReportBody audit={audit} />
    </div>
  );

  return (
    <Page
      trail={<Crumb href="/audits">{tNav("audits")}</Crumb>}
      title={<span className="truncate">{audit.workflowName}</span>}
      bleed
      actions={
        <div className="no-print flex items-center gap-0.5">
          <Tooltip label={t("exportPdf")}>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("exportPdf")}
              onClick={() => window.print()}
            >
              <Printer />
            </Button>
          </Tooltip>
          <Tooltip label={t("exportCsv")}>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t("exportCsv")}
              render={
                // oxlint-disable-next-line jsx-a11y/control-has-associated-label -- the label is on the Button that renders this element.
                <a href={`/api/v1/audits/${encodeURIComponent(audit.id)}/export.csv`} download />
              }
            >
              <Download />
            </Button>
          </Tooltip>
        </div>
      }
    >
      {wide ? (
        <Resizable className="h-[calc(100dvh-3.25rem)]">
          <ResizablePanel defaultSize={44} minSize={28} className="min-w-0 border-e border-line">
            <DocumentViewer audit={audit} />
          </ResizablePanel>
          <ResizableHandle
            aria-label={t("resize")}
            className="relative w-px bg-line outline-none transition-colors duration-150 after:absolute after:inset-y-0 after:-inset-x-1.5 hover:bg-accent focus-visible:bg-accent data-dragging:bg-accent"
          />
          <ResizablePanel minSize={36} className="min-w-0 overflow-y-auto overscroll-contain">
            {report}
          </ResizablePanel>
        </Resizable>
      ) : (
        <>
          {audit.documents.length > 0 && (
            <div className="h-[65dvh] min-h-80 border-b border-line">
              <DocumentViewer audit={audit} />
            </div>
          )}
          {report}
        </>
      )}
    </Page>
  );
}
