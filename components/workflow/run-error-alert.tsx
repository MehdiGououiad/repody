"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { CopyButton } from "@/components/workflow/api-panel/api-panel-copy";

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
      className="rounded-lg border border-fail/40 bg-fail/5 px-3 py-2.5 text-left space-y-1"
    >
      <p className="text-xs font-semibold text-fail-ink">{title}</p>
      <p className="text-xs text-fail-ink leading-relaxed">{message}</p>
      {runId ? (
        <div className="mt-2 pt-2 border-t border-fail/20 space-y-1.5">
          <p className="text-2xs text-ink-3">{t("test.errorRunIdHint")}</p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <code className="text-2xs font-mono bg-raised px-2 py-1 rounded break-all text-ink">
              {runId}
            </code>
            <CopyButton text={runId} />
            <Link
              href={`/audits/${runId}`}
              target="_blank"
              className="text-2xs font-medium text-accent-ink hover:underline"
            >
              {t("test.viewReport")}
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
