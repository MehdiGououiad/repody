"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { Filter, AtSign, CalendarDays, Hash, DollarSign, Percent, Sigma, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCrossHighlight } from "@/lib/stores/cross-highlight";
import { cn } from "@/lib/utils";
import type { AuditDetail, ExtractedField } from "@/lib/types";

const typeIconMap: Record<ExtractedField["type"], React.ElementType> = {
  string: AtSign,
  date: CalendarDays,
  number: Hash,
  currency: DollarSign,
  percent: Percent,
  calculated: Sigma,
};

export function ExtractedDataGrid({ audit }: { audit: AuditDetail }) {
  const tPanels = useTranslations("audits.detail.panels");
  const tFields = useTranslations("audits.detail.fields");
  const tCommon = useTranslations("common");
  const { hoveredFieldKey, selectedRuleId, setHoveredField } = useCrossHighlight();

  const failedKeysForSelectedRule = useMemo(() => {
    if (!selectedRuleId) return new Set<string>();
    const rule = audit.rules.find((r) => r.id === selectedRuleId);
    return new Set(rule?.affectedFieldKeys ?? []);
  }, [selectedRuleId, audit.rules]);

  return (
    <div className="flex flex-col h-full bg-card">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-container-low shrink-0">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
          {tPanels("extracted")}
        </h3>
        <Button variant="ghost" size="icon" className="h-7 w-7" aria-label={tCommon("filter")}>
          <Filter className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        {audit.extractedFields.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-on-surface-variant">
            <Inbox className="h-6 w-6 opacity-50" />
            <p className="text-sm">—</p>
          </div>
        ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-2/5">{tFields("key")}</TableHead>
              <TableHead className="text-right">{tFields("value")}</TableHead>
              <TableHead className="w-12 text-center">{tFields("type")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="font-mono text-xs">
            {audit.extractedFields.map((f) => {
              const Icon = typeIconMap[f.type] ?? AtSign;
              const isHovered = hoveredFieldKey === f.key;
              const isFailedForSelectedRule = failedKeysForSelectedRule.has(f.key);
              const isFailing = (f.failedRuleIds?.length ?? 0) > 0;
              return (
                <TableRow
                  key={f.key}
                  onMouseEnter={() => setHoveredField(f.key)}
                  onMouseLeave={() => setHoveredField(null)}
                  className={cn(
                    "cursor-pointer transition-colors",
                    isFailedForSelectedRule && "bg-danger/10 ring-1 ring-inset ring-danger/40",
                    !isFailedForSelectedRule && isFailing && "bg-danger/5",
                    isHovered && !isFailedForSelectedRule && "bg-surface-bright"
                  )}
                >
                  <TableCell
                    className={cn(
                      "py-2 text-on-surface-variant",
                      isFailing && "font-semibold text-on-surface"
                    )}
                  >
                    {f.key}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "py-2 text-right",
                      isFailing ? "font-semibold text-danger-strong" : "text-on-surface"
                    )}
                  >
                    {f.value}
                  </TableCell>
                  <TableCell className="py-2 text-center">
                    <Icon className="h-3.5 w-3.5 inline-block text-on-surface-variant" />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        )}
      </div>
    </div>
  );
}
