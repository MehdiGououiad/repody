"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fieldClassName } from "@/components/ui/input";
import { useCatalog } from "@/lib/hooks/use-catalog";
import type { SchemaField } from "@/lib/types";
import { cn } from "@/lib/utils";
import { importNuextractTemplate } from "@/lib/workflow/import-nuextract-template";

const EXAMPLE = `{
  "document_type": "string",
  "document_id": "verbatim-string",
  "holder_information": {
    "full_name": "string",
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "date"
  },
  "document_details": {
    "document_number": "verbatim-string",
    "valid_until_date": "date"
  }
}`;

export function ImportNuextractTemplateDialog({
  open,
  onOpenChange,
  hasExistingFields,
  onImport,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  hasExistingFields: boolean;
  onImport: (fields: SchemaField[], mode: "replace" | "append") => void;
}) {
  const t = useTranslations("workflows.builder.schema");
  const tCommon = useTranslations("common");
  const [raw, setRaw] = useState(EXAMPLE);
  const catalog = useCatalog();
  const [errorKey, setErrorKey] = useState<"invalid_json" | "not_object" | "empty" | null>(null);

  const apply = (mode: "replace" | "append") => {
    if (!catalog) return;
    const result = importNuextractTemplate(raw, catalog);
    if (!result.ok) {
      setErrorKey(result.error);
      return;
    }
    setErrorKey(null);
    onImport(result.fields, mode);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("importTemplateTitle")}</DialogTitle>
          <DialogDescription>{t("importTemplateDescription")}</DialogDescription>
        </DialogHeader>
        <textarea
          value={raw}
          onChange={(e) => {
            setRaw(e.target.value);
            setErrorKey(null);
          }}
          spellCheck={false}
          className={cn(
            fieldClassName,
            "min-h-64 w-full resize-y px-3 py-2 font-mono text-xs leading-relaxed"
          )}
          aria-label={t("importTemplateTitle")}
        />
        {errorKey ? (
          <p className="text-xs text-fail-ink">{t(`importTemplateError.${errorKey}`)}</p>
        ) : (
          <p className="text-xs text-ink-3">{t("importTemplateHint")}</p>
        )}
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            {tCommon("cancel")}
          </Button>
          {hasExistingFields ? (
            <Button type="button" variant="secondary" onClick={() => apply("append")}>
              {t("importTemplateAppend")}
            </Button>
          ) : null}
          <Button type="button" onClick={() => apply("replace")}>
            {hasExistingFields ? t("importTemplateReplace") : t("importTemplateApply")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
