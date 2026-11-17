"use client";

import { FileInput, FileInputDropzone, FileInputTrigger } from "@ui-sdk/react/file-input";
import { FileText, Upload, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { UPLOAD_ACCEPT } from "@/lib/uploads";
import { formatBytes } from "@/lib/utils";

function DocumentSlot({
  doc,
  file,
  maxSize,
  onFileChange,
}: {
  doc: DocumentDef;
  file: File | undefined;
  maxSize?: number;
  onFileChange: (file: File | null) => void;
}) {
  const t = useTranslations("workflows.builder.ingestion");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const fields = doc.schema.filter((f) => f.name.trim()).length;
  const [rejected, setRejected] = useState(false);

  return (
    <li className="grid grid-cols-1 items-center gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] sm:gap-4">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{doc.documentType}</p>
        <p className="text-xs text-ink-3">{t("fieldCount", { count: fields })}</p>
      </div>
      {file ? (
        <div className="flex h-10 items-center gap-2.5 rounded-md bg-raised ps-3 pe-1 shadow-[inset_0_0_0_1px_var(--line)]">
          <FileText className="size-4 shrink-0 text-ink-3" aria-hidden />
          <span className="min-w-0 flex-1 truncate text-sm text-ink">{file.name}</span>
          <span className="shrink-0 text-xs tabular-nums text-ink-3">
            {formatBytes(file.size, locale)}
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onFileChange(null)}
            aria-label={tCommon("remove")}
          >
            <X />
          </Button>
        </div>
      ) : (
        <FileInput
          accept={UPLOAD_ACCEPT}
          maxSize={maxSize}
          value={[]}
          onValueChange={([accepted]) => {
            setRejected(false);
            if (accepted) onFileChange(accepted);
          }}
          onReject={() => setRejected(true)}
        >
          <FileInputDropzone className="group rounded-md border border-dashed border-line-strong text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink-2 data-[dragging]:border-accent data-[dragging]:bg-accent-wash data-[dragging]:text-accent-ink">
            <FileInputTrigger className="flex h-10 w-full cursor-pointer items-center gap-2.5 rounded-md px-3 text-start text-sm focus-visible:outline-2 focus-visible:outline-focus">
              <Upload className="size-4 shrink-0" aria-hidden />
              <span className="truncate">{t("dropPrompt")}</span>
              <span className="ms-auto hidden shrink-0 text-xs text-ink-4 sm:inline">
                {t("fileHint")}
              </span>
            </FileInputTrigger>
          </FileInputDropzone>
        </FileInput>
      )}
      {rejected ? (
        <p role="alert" className="text-xs text-fail-ink sm:col-start-2">
          {t("fileRejected")}
        </p>
      ) : null}
    </li>
  );
}

/** One file slot per named document; `files` holds the chosen file of each. */
export function IngestionSection({
  documents,
  files,
  maxSize,
  onFilesChange,
}: {
  documents: DocumentDef[];
  rules?: WorkflowRule[];
  files: Record<string, File>;
  maxSize?: number;
  onFilesChange: (files: Record<string, File>) => void;
}) {
  const t = useTranslations("workflows.builder.ingestion");
  const named = documents.filter((d) => d.documentType.trim());
  if (named.length === 0) {
    return <p className="text-sm text-ink-3">{t("noDocsHint")}</p>;
  }
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]">
      {named.map((doc) => (
        <DocumentSlot
          key={doc.id}
          doc={doc}
          file={files[doc.id]}
          maxSize={maxSize}
          onFileChange={(file) => {
            const { [doc.id]: _replaced, ...rest } = files;
            onFilesChange(file ? { ...rest, [doc.id]: file } : rest);
          }}
        />
      ))}
    </ul>
  );
}
