"use client";

import { MoreHorizontal, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { fieldClassName } from "@/components/ui/input";
import type { DocumentDef } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SchemaTable } from "./schema-table";

/** One document type: its name (edited in place), optional instructions, and its fields. */
export function DocumentCard({
  doc,
  index,
  canRemove,
  onChange,
  onRemove,
}: {
  doc: DocumentDef;
  index: number;
  canRemove: boolean;
  onChange: (patch: Partial<DocumentDef>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [instructionsOpen, setInstructionsOpen] = useState(Boolean(doc.extractionInstructions));

  return (
    <section className="flex flex-col gap-4" aria-labelledby={`doc-type-${doc.id}`}>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={onRemove}
        title={t("docSource.removeTitle", {
          name: doc.documentType || `${t("docSource.unnamedDoc")} ${index + 1}`,
        })}
        description={tCommon("deleteWarning")}
        confirmLabel={tCommon("remove")}
      />
      <div className="flex items-center gap-2">
        <input
          id={`doc-type-${doc.id}`}
          aria-label={t("docSource.documentTypeLabel")}
          autoComplete="off"
          value={doc.documentType}
          onChange={(e) => onChange({ documentType: e.target.value })}
          placeholder={`${t("docSource.unnamedDoc")} ${index + 1}`}
          className="h-8 min-w-0 flex-1 rounded-md bg-transparent px-1.5 -ms-1.5 text-lg font-semibold text-ink outline-none transition-colors duration-100 placeholder:text-ink-4 hover:bg-hover focus-visible:bg-field focus-visible:shadow-[inset_0_0_0_1px_var(--accent)] focus-visible:outline-none"
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={t("docSource.documentActions")}>
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => setInstructionsOpen((v) => !v)}>
              {instructionsOpen
                ? t("docSource.hideInstructions")
                : t("docSource.extractionInstructionsLabel")}
            </DropdownMenuItem>
            {canRemove ? (
              <DropdownMenuItem
                onSelect={() => setConfirmOpen(true)}
                className="text-fail-ink focus:text-fail-ink [&_svg]:text-fail-ink"
              >
                <Trash2 />
                {t("docSource.removeDocument")}
              </DropdownMenuItem>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {instructionsOpen ? (
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-ink-2">
            {t("docSource.extractionInstructionsLabel")}
          </span>
          <textarea
            name={`document-instructions-${doc.id}`}
            value={doc.extractionInstructions ?? ""}
            onChange={(e) => onChange({ extractionInstructions: e.target.value })}
            placeholder={t("docSource.extractionInstructionsPlaceholder")}
            rows={3}
            className={cn(fieldClassName, "min-h-[72px] w-full resize-y px-2.5 py-2")}
          />
          <span className="text-xs text-ink-3">{t("docSource.extractionInstructionsHint")}</span>
        </label>
      ) : null}

      <SchemaTable schema={doc.schema} onChange={(schema) => onChange({ schema })} />
    </section>
  );
}
