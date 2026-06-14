"use client";

import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { AuditStatus } from "@/lib/types";

const variantMap: Record<AuditStatus, "success" | "danger" | "warning" | "info"> = {
  passed: "success",
  failed: "danger",
  warning: "warning",
  running: "info",
};

interface StatusBadgeProps {
  status: AuditStatus;
  failedCount?: number;
  className?: string;
}

export function StatusBadge({ status, failedCount, className }: StatusBadgeProps) {
  const t = useTranslations("audits.status");
  const label =
    status === "failed" && failedCount
      ? t("failedWithRules", { count: failedCount })
      : t(status);

  return (
    <Badge variant={variantMap[status]} withDot className={cn("font-semibold", className)}>
      {label}
    </Badge>
  );
}
