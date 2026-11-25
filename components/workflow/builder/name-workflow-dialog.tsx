"use client";

import { Field, FieldDescription, FieldLabel } from "@ui-sdk/react/field";
import { useTranslations } from "next-intl";
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
import { Input } from "@/components/ui/input";

/**
 * The first step of a new workflow: its name, and the name of the first document it reads, so
 * neither is forgotten and the builder opens ready to add fields.
 */
export function NameWorkflowDialog({
  open,
  onStart,
  onCancel,
}: {
  open: boolean;
  onStart: (names: { workflow: string; document: string }) => void;
  onCancel: () => void;
}) {
  const t = useTranslations("workflows.builder.start");
  const tCommon = useTranslations("common");
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            onStart({
              workflow: String(data.get("workflow") ?? "").trim(),
              document: String(data.get("document") ?? "").trim(),
            });
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("title")}</DialogTitle>
            <DialogDescription>{t("hint")}</DialogDescription>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-4">
            <Field name="workflow">
              <FieldLabel className="text-xs font-medium text-ink-2">
                {t("workflowName")}
              </FieldLabel>
              <Input
                required
                // oxlint-disable-next-line jsx-a11y/no-autofocus -- a dialog moves focus to its first field when it opens.
                autoFocus
                autoComplete="off"
                placeholder={t("workflowPlaceholder")}
                className="mt-1"
              />
            </Field>
            <Field name="document">
              <FieldLabel className="text-xs font-medium text-ink-2">
                {t("documentName")}
              </FieldLabel>
              <Input
                required
                autoComplete="off"
                placeholder={t("documentPlaceholder")}
                className="mt-1"
              />
              <FieldDescription className="mt-1 text-xs text-ink-3">
                {t("documentHint")}
              </FieldDescription>
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onCancel}>
              {tCommon("cancel")}
            </Button>
            <Button type="submit" variant="primary">
              {t("create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
