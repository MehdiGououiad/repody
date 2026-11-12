"use client";

import { FileText, Upload, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { cn, formatBytes } from "@/lib/utils";

/** The file types the API accepts (AUDIT_UPLOAD_ALLOWED_MIME_TYPES defaults). */
const ACCEPT = {
  "application/pdf": [".pdf"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/webp": [".webp"],
};

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
  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    accept: ACCEPT,
    maxFiles: 1,
    maxSize,
    multiple: false,
    onDropAccepted: ([accepted]) => onFileChange(accepted ?? null),
  });

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
        <div
          {...getRootProps({
            className: cn(
              "flex h-10 cursor-pointer items-center gap-2.5 rounded-md border border-dashed px-3 text-sm transition-colors duration-100 focus-visible:outline-2 focus-visible:outline-focus",
              isDragActive
                ? "border-accent bg-accent-wash text-accent-ink"
                : "border-line-strong text-ink-3 hover:bg-hover hover:text-ink-2"
            ),
          })}
        >
          <input {...getInputProps({ name: `upload-${doc.id}` })} />
          <Upload className="size-4 shrink-0" aria-hidden />
          <span className="truncate">{t("dropPrompt")}</span>
          <span className="ms-auto hidden shrink-0 text-xs text-ink-4 sm:inline">
            {t("fileHint")}
          </span>
        </div>
      )}
      {fileRejections.length ? (
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
