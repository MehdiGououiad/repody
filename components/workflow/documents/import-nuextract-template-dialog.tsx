"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileJson2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { importNuextractTemplate } from "@/lib/workflow/import-nuextract-template";
import type { SchemaField } from "@/lib/types";

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
  const [errorKey, setErrorKey] = useState<"invalid_json" | "not_object" | "empty" | null>(
    null
  );

  const apply = (mode: "replace" | "append") => {
    const result = importNuextractTemplate(raw);
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
          className="min-h-64 w-full rounded-md border border-border bg-surface-container-low px-3 py-2 font-mono text-xs leading-relaxed text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
          aria-label={t("importTemplateTitle")}
        />
        {errorKey ? (
          <p className="text-xs text-danger">{t(`importTemplateError.${errorKey}`)}</p>
        ) : (
          <p className="text-[11px] text-on-surface-variant">{t("importTemplateHint")}</p>
        )}
        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            {tCommon("cancel")}
          </Button>
          {hasExistingFields ? (
            <Button type="button" variant="outline" onClick={() => apply("append")}>
              {t("importTemplateAppend")}
            </Button>
          ) : null}
          <Button type="button" onClick={() => apply("replace")}>
            <FileJson2 className="h-3.5 w-3.5" />
            {hasExistingFields ? t("importTemplateReplace") : t("importTemplateApply")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
