"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Upload, FileText, X, CheckCircle2,
  ChevronDown, ChevronUp, ShieldCheck, Tag, AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

interface UploadedFile { name: string; size: string; }

export type { UploadedFile };

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocUploadCardProps {
  doc: DocumentDef;
  rules: WorkflowRule[];
  onFileChange: (docId: string, file: UploadedFile | null, raw?: File) => void;
  uploadedFile: UploadedFile | null;
}

function DocUploadCard({ doc, rules, onFileChange, uploadedFile }: DocUploadCardProps) {
  const t = useTranslations("workflows.builder.ingestion");
  const tCommon = useTranslations("common");
  const [dragging, setDragging] = useState(false);
  const [fieldsOpen, setFieldsOpen] = useState(true);
  const [rulesOpen, setRulesOpen] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  const docRules = rules.filter((r) => r.appliesTo.includes(doc.id));
  const docName = doc.documentType.trim() || t("unnamedDoc");
  const namedFields = doc.schema.filter((f) => f.name.trim());

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const f = fileList[0];
    onFileChange(doc.id, { name: f.name, size: formatBytes(f.size) }, f);
    // Allow picking the same file again (browsers skip onChange otherwise).
    if (inputRef.current) inputRef.current.value = "";
  };

  const severityLabels = {
    reject: t("severityReject"),
    flag: t("severityFlag"),
    info: t("severityInfo"),
  };

  return (
    <div className="rounded-xl panel-elevated overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-surface-container-low border-b border-border">
        <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <FileText className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-on-surface truncate">{docName}</p>
          <p className="text-[11px] text-on-surface-variant">
            {namedFields.length} {namedFields.length !== 1 ? t("fieldPlural") : t("fieldSingular")}
            {docRules.length > 0 && ` · ${docRules.length} ${t("ruleCount")}`}
          </p>
        </div>
        {uploadedFile && (
          <Badge variant="success" className="gap-1 text-[10px] shrink-0">
            <CheckCircle2 className="h-3 w-3" />
            {t("fileReady")}
          </Badge>
        )}
      </div>

      <div className="p-4 space-y-3">
        {/* Fields to extract */}
        {namedFields.length > 0 && (
          <div className="rounded-lg border border-border bg-surface-container-lowest overflow-hidden">
            <button
              onClick={() => setFieldsOpen((o) => !o)}
              className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
            >
              <div className="flex items-center gap-2">
                <Tag className="h-3.5 w-3.5 text-on-surface-variant" />
                <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  {t("fieldsToExtract")}
                </span>
              </div>
              {fieldsOpen ? <ChevronUp className="h-3.5 w-3.5 text-on-surface-variant" /> : <ChevronDown className="h-3.5 w-3.5 text-on-surface-variant" />}
            </button>
            {fieldsOpen && (
              <div className="px-3 pb-2 divide-y divide-border">
                {namedFields.map((f) => (
                  <div key={f.id} className="py-1.5 flex items-start gap-2">
                    <code className="text-[11px] font-mono text-primary bg-primary/8 px-1.5 py-0.5 rounded shrink-0">{f.name}</code>
                    {f.description && (
                      <span className="text-[11px] text-on-surface-variant leading-relaxed">{f.description}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Validation rules */}
        {docRules.length > 0 && (
          <div className="rounded-lg border border-border bg-surface-container-lowest overflow-hidden">
            <button
              onClick={() => setRulesOpen((o) => !o)}
              className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
            >
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-on-surface-variant" />
                <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  {t("validationRulesLabel")}
                </span>
              </div>
              {rulesOpen ? <ChevronUp className="h-3.5 w-3.5 text-on-surface-variant" /> : <ChevronDown className="h-3.5 w-3.5 text-on-surface-variant" />}
            </button>
            {rulesOpen && (
              <div className="px-3 pb-2 divide-y divide-border">
                {docRules.map((r) => (
                  <div key={r.id} className="py-1.5 flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-[11px] font-medium text-on-surface truncate">{r.name}</p>
                      <p className="text-[10px] text-on-surface-variant font-mono truncate mt-0.5">{r.body}</p>
                    </div>
                    {/* severity label */}
                    {r.severity === "reject" ? (
                      <span className="inline-flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-danger shrink-0">
                        <AlertTriangle className="h-2.5 w-2.5" />{severityLabels.reject}
                      </span>
                    ) : r.severity === "flag" ? (
                      <span className="inline-flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-warning shrink-0">
                        <AlertTriangle className="h-2.5 w-2.5" />{severityLabels.flag}
                      </span>
                    ) : (
                      <span className="text-[9px] font-semibold uppercase tracking-wide text-on-surface-variant shrink-0">
                        {severityLabels.info}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Drop zone / uploaded file */}
        {uploadedFile ? (
          <div className="flex items-center gap-3 p-3 rounded-lg border border-success/40 bg-success/5">
            <FileText className="h-4 w-4 text-success shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-on-surface truncate">{uploadedFile.name}</p>
              <p className="text-xs text-on-surface-variant">{uploadedFile.size}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-on-surface-variant hover:text-danger"
              onClick={() => {
                if (inputRef.current) inputRef.current.value = "";
                onFileChange(doc.id, null, undefined);
              }}
              aria-label={tCommon("remove")}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <>
            <input
              id={`upload-input-${doc.id}`}
              ref={inputRef}
              type="file"
              name={`upload-${doc.id}`}
              accept=".pdf,.csv,.json,.xlsx"
              className="sr-only"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <label
              htmlFor={`upload-input-${doc.id}`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
              className={cn(
                "rounded-lg border-2 border-dashed p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-colors",
                dragging ? "border-primary bg-primary/5" : "border-outline-variant hover:border-outline hover:bg-surface-container-low"
              )}
            >
              <Upload className="h-5 w-5 text-on-surface-variant mb-2" aria-hidden="true" />
              <p className="text-xs font-medium text-on-surface">
                {t("uploadPrompt", { name: docName })}
              </p>
              <p className="text-[10px] text-on-surface-variant mt-1">{t("fileHint")}</p>
            </label>
          </>
        )}
      </div>
    </div>
  );
}

export function IngestionSection({
  documents,
  rules,
  onActiveSampleChange,
  onFilesChange,
  uploads: controlledUploads,
  filesByDocId: controlledFiles,
}: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  onActiveSampleChange?: (docId: string, fileName: string) => void;
  onFilesChange?: (files: Record<string, File>) => void;
  /** When set, upload UI is controlled by the parent (survives step/tab changes). */
  uploads?: Record<string, UploadedFile | null>;
  filesByDocId?: Record<string, File>;
}) {
  const t = useTranslations("workflows.builder.ingestion");
  const [internalUploads, setInternalUploads] = useState<Record<string, UploadedFile | null>>({});
  const [internalFiles, setInternalFiles] = useState<Record<string, File>>({});

  const isControlled = controlledUploads !== undefined;
  const uploads = isControlled ? controlledUploads : internalUploads;
  const filesByDoc = isControlled ? (controlledFiles ?? {}) : internalFiles;

  const handleFileChange = (docId: string, file: UploadedFile | null, raw?: File) => {
    const nextUploads = { ...uploads, [docId]: file };
    const nextFiles = { ...filesByDoc };
    if (raw) nextFiles[docId] = raw;
    else delete nextFiles[docId];

    if (!isControlled) {
      setInternalUploads(nextUploads);
      setInternalFiles(nextFiles);
    }
    onFilesChange?.(nextFiles);
    if (file) onActiveSampleChange?.(docId, file.name);
    else onActiveSampleChange?.(docId, "");
  };

  const validDocs = documents.filter((d) => d.documentType.trim());

  if (validDocs.length === 0) {
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
      {validDocs.map((doc) => (
        <DocUploadCard
          key={doc.id}
          doc={doc}
          rules={rules}
          uploadedFile={uploads[doc.id] ?? null}
          onFileChange={handleFileChange}
        />
      ))}
    </div>
  );
}
