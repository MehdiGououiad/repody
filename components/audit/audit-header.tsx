"use client";

import { useLocale, useTranslations } from "next-intl";
import { Download, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/status-badge";
import type { AuditDetail } from "@/lib/types";

export function AuditHeader({ audit }: { audit: AuditDetail }) {
  const locale = useLocale();
  const t = useTranslations("audits.detail");
  const tCommon = useTranslations("common");
  const ts = new Date(audit.timestamp).toLocaleString(locale, {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  return (
    <div className="bg-card border-b border-border px-6 py-4 flex items-start justify-between gap-4 flex-wrap">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <StatusBadge status={audit.status} failedCount={audit.failedRules} />
          <span className="text-xs text-on-surface-variant font-mono">
            {t("auditId")}: {audit.id}
          </span>
        </div>
        <h2 className="text-2xl font-semibold tracking-tight text-on-surface">
          {t("title")}
        </h2>
        <p className="text-sm text-on-surface-variant mt-1">
          {t("processed")}: {ts} • {t("entity")}:{" "}
          <span className="font-medium">{audit.entity}</span> • {t("workflow")}:{" "}
          <span className="font-medium">{audit.workflowName}</span>
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline">
          <Download className="h-4 w-4" />
          {tCommon("export")}
        </Button>
        <Button>
          <RotateCw className="h-4 w-4" />
          {tCommon("rerunAudit")}
        </Button>
      </div>
    </div>
  );
}
