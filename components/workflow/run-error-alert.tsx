"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { StatusGlyph } from "@/components/ui/status-glyph";

/** What went wrong with a run, in plain words, and where to look next. */
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
    <div role="alert" className="flex gap-3 rounded-lg bg-fail-wash/60 px-4 py-3">
      <StatusGlyph status="failed" className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">{title}</p>
        <p className="mt-0.5 break-words text-sm text-ink-2">{message}</p>
        {runId ? (
          <p className="mt-2 text-xs text-ink-3">
            <span className="font-mono">{runId}</span>
            {" · "}
            <Link
              href={`/audits/${runId}`}
              target="_blank"
              className="text-accent-ink hover:underline"
            >
              {t("test.viewReport")}
            </Link>
          </p>
        ) : null}
      </div>
    </div>
  );
}
