"use client";

import { AlertTriangle, ChevronDown, FileText, ShieldCheck, Tag, Upload, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useDropzone } from "react-dropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { conditionFields } from "@/lib/rules/conditions";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { cn, formatBytes } from "@/lib/utils";

/** The file types the API accepts (AUDIT_UPLOAD_ALLOWED_MIME_TYPES defaults). */
const ACCEPT = {
  "application/pdf": [".pdf"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/webp": [".webp"],
};

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Tag;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Collapsible
      defaultOpen
      className="rounded-lg border border-border bg-surface-container-lowest overflow-hidden"
    >
      <CollapsibleTrigger className="group w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-container-low transition-colors">
        <span className="flex items-center gap-2">
          <Icon className="h-3.5 w-3.5 text-on-surface-variant" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
            {title}
          </span>
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-on-surface-variant transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-3 pb-2 divide-y divide-border">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}

function DocUploadCard({
  doc,
  rules,
  file,
  maxSize,
  onFileChange,
}: {
  doc: DocumentDef;
  rules: WorkflowRule[];
  file: File | undefined;
  maxSize?: number;
  onFileChange: (file: File | null) => void;
}) {
  const t = useTranslations("workflows.builder.ingestion");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const docRules = rules.filter((r) => r.appliesTo.includes(doc.id));
  const docName = doc.documentType.trim() || t("unnamedDoc");
  const namedFields = doc.schema.filter((f) => f.name.trim());
  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    accept: ACCEPT,
    maxFiles: 1,
    maxSize,
    multiple: false,
    onDropAccepted: ([accepted]) => onFileChange(accepted ?? null),
  });

  return (
    <div className="rounded-xl panel-elevated overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3 bg-surface-container-low border-b border-border">
        <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <FileText className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-on-surface truncate">{docName}</p>
          <p className="text-[11px] text-on-surface-variant">
            {t("fieldCount", { count: namedFields.length })}
            {docRules.length > 0 && ` · ${t("ruleCount", { count: docRules.length })}`}
          </p>
        </div>
        {file ? (
          <Badge variant="success" className="gap-1 text-[10px] shrink-0">
            {t("fileReady")}
          </Badge>
        ) : null}
      </div>

      <div className="p-4 space-y-3">
        {namedFields.length > 0 ? (
          <Section icon={Tag} title={t("fieldsToExtract")}>
            {namedFields.map((f) => (
              <div key={f.id} className="py-1.5 flex items-start gap-2">
                <code className="text-[11px] font-mono text-primary bg-primary/8 px-1.5 py-0.5 rounded shrink-0">
                  {f.name}
                </code>
                {f.description ? (
                  <span className="text-[11px] text-on-surface-variant leading-relaxed">
                    {f.description}
                  </span>
                ) : null}
              </div>
            ))}
          </Section>
        ) : null}

        {docRules.length > 0 ? (
          <Section icon={ShieldCheck} title={t("validationRulesLabel")}>
            {docRules.map((r) => (
              <div key={r.id} className="py-1.5 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[11px] font-medium text-on-surface truncate">{r.name}</p>
                  <p className="text-[10px] text-on-surface-variant font-mono truncate mt-0.5">
                    {r.conditions.flatMap(conditionFields).join(", ")}
                  </p>
                </div>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide shrink-0",
                    r.severity === "reject" ? "text-danger" : "text-warning"
                  )}
                >
                  <AlertTriangle className="h-2.5 w-2.5" />
                  {r.severity === "reject" ? t("severityReject") : t("severityFlag")}
                </span>
              </div>
            ))}
          </Section>
        ) : null}

        {file ? (
          <div className="flex items-center gap-3 p-3 rounded-lg border border-success/40 bg-success/5">
            <FileText className="h-4 w-4 text-success shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-on-surface truncate">{file.name}</p>
              <p className="text-xs text-on-surface-variant">{formatBytes(file.size, locale)}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-on-surface-variant hover:text-danger"
              onClick={() => onFileChange(null)}
              aria-label={tCommon("remove")}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <div
            {...getRootProps({
              className: cn(
                "rounded-lg border-2 border-dashed p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-colors focus-visible:outline-2 focus-visible:outline-ring",
                isDragActive
                  ? "border-primary bg-primary/5"
                  : "border-outline-variant hover:border-outline hover:bg-surface-container-low"
              ),
            })}
          >
            <input {...getInputProps({ name: `upload-${doc.id}` })} />
            <Upload className="h-5 w-5 text-on-surface-variant mb-2" aria-hidden="true" />
            <p className="text-xs font-medium text-on-surface">
              {t("uploadPrompt", { name: docName })}
            </p>
            <p className="text-[10px] text-on-surface-variant mt-1">{t("fileHint")}</p>
            {fileRejections.length > 0 ? (
              <p role="alert" className="text-[11px] text-danger mt-2">
                {t("fileRejected")}
              </p>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

/** One upload card per named workflow document; `files` holds the chosen file of each. */
export function IngestionSection({
  documents,
  rules,
  files,
  maxSize,
  onFilesChange,
}: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  files: Record<string, File>;
  maxSize?: number;
  onFilesChange: (files: Record<string, File>) => void;
}) {
  const t = useTranslations("workflows.builder.ingestion");
  const named = documents.filter((d) => d.documentType.trim());

  if (named.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center text-on-surface-variant gap-2">
        <FileText className="h-8 w-8 opacity-30" />
        <p className="text-sm">{t("noDocs")}</p>
        <p className="text-xs">{t("noDocsHint")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {named.map((doc) => (
        <DocUploadCard
          key={doc.id}
          doc={doc}
          rules={rules}
          file={files[doc.id]}
          maxSize={maxSize}
          onFileChange={(file) => {
            const { [doc.id]: _replaced, ...rest } = files;
            onFilesChange(file ? { ...rest, [doc.id]: file } : rest);
          }}
        />
      ))}
    </div>
  );
}
