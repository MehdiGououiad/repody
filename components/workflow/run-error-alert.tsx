"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { CopyButton } from "@/components/workflow/api-panel-copy";

export function RunErrorAlert({
  title,
  message,
  runId,
}: {
  title: string;
  message: string;
  runId?: string | null;
}) {
  const t = useTranslations("workflows.builder");

  return (
    <div
      role="alert"
      className="rounded-lg border border-danger/40 bg-danger/5 px-3 py-2.5 text-left space-y-1"
    >
      <p className="text-xs font-semibold text-danger">{title}</p>
      <p className="text-xs text-danger-strong leading-relaxed">{message}</p>
      {runId ? (
        <div className="mt-2 pt-2 border-t border-danger/20 space-y-1.5">
          <p className="text-[10px] text-on-surface-variant">{t("test.errorRunIdHint")}</p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <code className="text-[11px] font-mono bg-surface-container px-2 py-1 rounded break-all text-on-surface">
              {runId}
            </code>
            <CopyButton text={runId} />
            <Link
              href={`/audits/${runId}`}
              target="_blank"
              className="text-[10px] font-medium text-accent-blue hover:underline"
            >
              {t("test.viewReport")}
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
