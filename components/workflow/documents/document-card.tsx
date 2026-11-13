"use client";

import { MoreHorizontal, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { BareInput, inlineFieldClass, Textarea } from "@/components/ui/input";
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { confirmAction } from "@/components/ui/overlays";
import type { DocumentDef } from "@/lib/types";
import { cn } from "@/lib/utils";
import { type FieldResult, SchemaTable } from "./schema-table";

/** One document type: its name (edited in place), optional instructions, and its fields. */
export function DocumentCard({
  doc,
  index,
  canRemove,
  results,
  staleFields,
  actions,
  onChange,
  onRemove,
}: {
  doc: DocumentDef;
  index: number;
  canRemove: boolean;
  results?: Map<string, FieldResult>;
  staleFields?: Set<string>;
  actions?: React.ReactNode;
  onChange: (patch: Partial<DocumentDef>) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const [instructionsOpen, setInstructionsOpen] = useState(Boolean(doc.extractionInstructions));
  const name = doc.documentType || `${t("docSource.unnamedDoc")} ${index + 1}`;

  return (
    <section className="flex min-h-0 flex-col" aria-labelledby={`doc-type-${doc.id}`}>
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line px-3">
        <BareInput
          id={`doc-type-${doc.id}`}
          aria-label={t("docSource.documentTypeLabel")}
          autoComplete="off"
          value={doc.documentType}
          onChange={(e) => onChange({ documentType: e.target.value })}
          placeholder={name}
          className={cn(inlineFieldClass, "h-7 flex-1 text-[15px] font-semibold")}
        />
        {actions}
        <Menu
          onAction={async (value) => {
            if (value === "instructions") setInstructionsOpen((open) => !open);
            if (value === "remove") {
              const yes = await confirmAction({
                title: t("docSource.removeTitle", { name }),
                description: tCommon("deleteWarning"),
                confirmLabel: tCommon("remove"),
                cancelLabel: tCommon("cancel"),
                danger: true,
              });
              if (yes) onRemove();
            }
          }}
        >
          <MenuTrigger
            render={
              <Button variant="ghost" size="icon-sm" aria-label={t("docSource.documentActions")}>
                <MoreHorizontal />
              </Button>
            }
          />
          <MenuContent align="end">
            <MenuItem value="instructions">
              {instructionsOpen
                ? t("docSource.hideInstructions")
                : t("docSource.extractionInstructionsLabel")}
            </MenuItem>
            {canRemove ? (
              <>
                <MenuSeparator />
                <MenuItem value="remove" danger>
                  <Trash2 />
                  {t("docSource.removeDocument")}
                </MenuItem>
              </>
            ) : null}
          </MenuContent>
        </Menu>
      </div>

      {instructionsOpen ? (
        <label className="flex flex-col gap-1.5 border-b border-line bg-raised px-3 py-2.5">
          <span className="text-xs font-medium text-ink-2">
            {t("docSource.extractionInstructionsLabel")}
          </span>
          <Textarea
            name={`document-instructions-${doc.id}`}
            value={doc.extractionInstructions ?? ""}
            onChange={(e) => onChange({ extractionInstructions: e.target.value })}
            placeholder={t("docSource.extractionInstructionsPlaceholder")}
            rows={2}
            className="min-h-14"
          />
          <span className="text-xs text-ink-4">{t("docSource.extractionInstructionsHint")}</span>
        </label>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <SchemaTable
          schema={doc.schema}
          results={results}
          staleFields={staleFields}
          onChange={(schema) => onChange({ schema })}
        />
      </div>
    </section>
  );
}
