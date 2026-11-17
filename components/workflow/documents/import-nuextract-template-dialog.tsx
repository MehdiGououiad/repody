"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/input";
import { catalog } from "@/lib/catalog";
import type { SchemaField } from "@/lib/types";
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
  const [errorKey, setErrorKey] = useState<"invalid_json" | "not_object" | "empty" | null>(null);

  const apply = (mode: "replace" | "append") => {
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
      <DialogBackdrop />
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>{t("importTemplateTitle")}</DialogTitle>
          <DialogDescription>{t("importTemplateDescription")}</DialogDescription>
        </DialogHeader>
        <DialogBody className="flex flex-col gap-2">
          <Textarea
            value={raw}
            onChange={(e) => {
              setRaw(e.target.value);
              setErrorKey(null);
            }}
            spellCheck={false}
            className="min-h-64 font-mono text-xs"
            aria-label={t("importTemplateTitle")}
          />
          {errorKey ? (
            <p className="text-xs text-fail-ink">{t(`importTemplateError.${errorKey}`)}</p>
          ) : (
            <p className="text-xs text-ink-3">{t("importTemplateHint")}</p>
          )}
        </DialogBody>
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            {tCommon("cancel")}
          </Button>
          {hasExistingFields ? (
            <Button type="button" variant="secondary" onClick={() => apply("append")}>
              {t("importTemplateAppend")}
            </Button>
          ) : null}
          <Button type="button" variant="primary" onClick={() => apply("replace")}>
            {hasExistingFields ? t("importTemplateReplace") : t("importTemplateApply")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
