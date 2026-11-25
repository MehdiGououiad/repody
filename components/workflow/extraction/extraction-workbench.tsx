"use client";

import {
  createFileInputController,
  FileInput,
  FileInputDropzone,
  FileInputTrigger,
} from "@ui-sdk/react/file-input";
import { Resizable, ResizableHandle, ResizablePanel } from "@ui-sdk/react/resizable";
import { FileUp, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useCan } from "@/components/auth/access-context";
import { DocChip } from "@/components/shared/doc-chip";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import type { TestRun } from "@/components/workflow/builder/use-test-run";
import { DocumentCard } from "@/components/workflow/documents/document-card";
import type { FieldResult } from "@/components/workflow/documents/schema-table";
import { useMediaQuery } from "@/lib/hooks/use-media-query";
import { fieldKey } from "@/lib/rules/field-key";
import type { DocumentDef } from "@/lib/types";
import { UPLOAD_ACCEPT } from "@/lib/uploads";
import { newDocument } from "@/lib/workflow/new-items";

/** "facture_mars-2026.pdf" -> "Facture mars 2026": a document name from its file. */
function nameFromFile(fileName: string): string {
  const base = fileName
    .replace(/\.[^.]+$/, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return base ? base.charAt(0).toUpperCase() + base.slice(1) : "";
}

function SamplePane({
  file,
  onFileChange,
}: {
  file: File | undefined;
  onFileChange: (file: File | null) => void;
}) {
  const t = useTranslations("workflows.builder.workbench");
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => (url ? URL.revokeObjectURL(url) : undefined), [url]);
  const [picker] = useState(createFileInputController);

  return (
    <FileInput
      controller={picker}
      accept={UPLOAD_ACCEPT}
      value={[]}
      className="h-full"
      onValueChange={([accepted]) => {
        if (accepted) onFileChange(accepted);
      }}
    >
      {/* The whole pane takes a drop; the visible buttons open the picker. */}
      <FileInputDropzone className="group relative flex h-full min-h-0 flex-col bg-canvas outline-none">
        {file && url ? (
          <>
            <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line px-3">
              <span className="min-w-0 flex-1 truncate text-[13px] text-ink-2">{file.name}</span>
              <Button variant="ghost" size="xs" onClick={() => picker.open()}>
                <FileUp />
                {t("replace")}
              </Button>
              <Button
                variant="ghost"
                size="icon-xs"
                aria-label={t("removeSample")}
                onClick={() => onFileChange(null)}
              >
                <X />
              </Button>
            </div>
            {file.type === "application/pdf" ? (
              <iframe
                src={`${url}#toolbar=0&navpanes=0&view=FitH`}
                title={file.name}
                className="min-h-0 w-full flex-1 bg-canvas"
              />
            ) : (
              <div className="min-h-0 flex-1 overflow-auto p-4">
                {/* oxlint-disable-next-line nextjs/no-img-element -- a local sample, shown as dropped. */}
                <img
                  src={url}
                  alt={file.name}
                  className="mx-auto h-auto max-w-full rounded-md shadow-panel"
                />
              </div>
            )}
          </>
        ) : (
          <FileInputTrigger className="m-auto flex aspect-[1/1.2] w-[min(320px,calc(100%-2rem))] cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-line-strong bg-panel px-6 text-center transition-[border-color,background-color,scale] duration-150 hover:border-accent hover:bg-accent-wash/40 active:scale-[0.99] group-data-[dragging]:border-accent group-data-[dragging]:bg-accent-wash">
            <span className="flex size-10 items-center justify-center rounded-full bg-panel text-ink-3 shadow-panel transition-transform duration-300 group-data-[dragging]:-translate-y-1 group-data-[dragging]:scale-105">
              <FileUp className="size-4" aria-hidden />
            </span>
            <span className="text-[13px] font-medium text-ink">{t("samplePrompt")}</span>
            <span className="max-w-64 text-xs text-ink-3">{t("sampleHint")}</span>
          </FileInputTrigger>
        )}
        {file ? (
          <div className="pointer-events-none absolute inset-2 hidden rounded-xl border-2 border-dashed border-accent bg-accent-wash group-data-[dragging]:block" />
        ) : null}
      </FileInputDropzone>
    </FileInput>
  );
}

export function ExtractionWorkbench({
  documents,
  test,
  onChange,
}: {
  documents: DocumentDef[];
  test: TestRun;
  onChange: (documents: DocumentDef[]) => void;
}) {
  const t = useTranslations("workflows.builder.workbench");
  const tDoc = useTranslations("workflows.builder.docSource");
  const [activeId, setActiveId] = useState(documents[0]?.id);
  const active = documents.find((d) => d.id === activeId) ?? documents[0];
  const activeIndex = documents.indexOf(active);
  const wide = useMediaQuery("(min-width: 1024px)");
  const canEdit = useCan("workflow:write");

  const results = useMemo(() => {
    const byDoc = new Map<string, Map<string, FieldResult>>();
    if (test.run.phase !== "done") return byDoc;
    for (const doc of documents) {
      const found = test.run.result.documents.find(
        (d) => d.documentType.trim() === doc.documentType.trim(),
      );
      if (!found) continue;
      byDoc.set(
        doc.id,
        new Map(
          found.fields.map((f) => [fieldKey(f.key), { extracted: f.extracted, value: f.value }]),
        ),
      );
    }
    return byDoc;
  }, [test.run, documents]);
  const stale = new Set(active?.schema.filter(test.isStale).map((f) => f.id) ?? []);
  const activeResults = active ? results.get(active.id) : undefined;
  const found = activeResults ? [...activeResults.values()].filter((r) => r.extracted).length : 0;

  if (!active) return null;
  const updateDoc = (patch: Partial<DocumentDef>) =>
    onChange(documents.map((d) => (d.id === active.id ? { ...d, ...patch } : d)));
  const setFile = (file: File | null) => {
    test.setFile(active.id, file);
    if (file && !active.documentType.trim()) updateDoc({ documentType: nameFromFile(file.name) });
  };

  const fieldsPane = (
    // Read-only roles see the schema with every control disabled (the API refuses saves too).
    <fieldset disabled={!canEdit} className="contents">
      <DocumentCard
        key={active.id}
        doc={active}
        index={activeIndex}
        canRemove={documents.length > 1}
        results={activeResults}
        staleFields={stale}
        onChange={updateDoc}
        onRemove={() => {
          const rest = documents.filter((d) => d.id !== active.id);
          onChange(rest);
          setActiveId(rest[0]?.id);
        }}
        actions={
          activeResults ? (
            <span className="shrink-0 text-xs tabular-nums text-ink-3">
              {t("found", { found, total: activeResults.size })}
            </span>
          ) : undefined
        }
      />
    </fieldset>
  );

  return (
    <Tabs
      value={active.id}
      onValueChange={(value) => value && setActiveId(String(value))}
      className="flex h-full min-h-0 flex-col"
    >
      <div className="flex h-10 shrink-0 items-center gap-1 overflow-x-auto border-b border-line bg-panel px-2">
        <TabsList aria-label={tDoc("title")}>
          {documents.map((doc, index) => (
            <TabsTab key={doc.id} value={doc.id}>
              <DocChip index={index}>
                {doc.documentType || `${tDoc("unnamedDoc")} ${index + 1}`}
              </DocChip>
              <span className="text-xs tabular-nums text-ink-4">
                {doc.schema.filter((f) => f.name.trim()).length}
              </span>
              {test.files[doc.id] ? (
                <span className="size-1.5 rounded-full bg-pass" aria-hidden />
              ) : null}
            </TabsTab>
          ))}
        </TabsList>
        {canEdit ? (
          <Button
            variant="ghost"
            size="xs"
            aria-label={tDoc("addDocument")}
            onClick={() => {
              const doc = newDocument();
              onChange([...documents, doc]);
              setActiveId(doc.id);
            }}
          >
            <Plus />
            {t("addDocument")}
          </Button>
        ) : null}
      </div>

      <TabsPanel value={active.id} className="relative min-h-0 flex-1">
        <Resizable
          key={wide ? "row" : "column"}
          orientation={wide ? "horizontal" : "vertical"}
          className="h-full"
        >
          <ResizablePanel
            defaultSize={wide ? 46 : 36}
            minSize={wide ? 26 : 20}
            className="min-h-0 min-w-0 overflow-hidden"
          >
            <SamplePane key={active.id} file={test.files[active.id]} onFileChange={setFile} />
          </ResizablePanel>
          <ResizableHandle
            aria-label={t("resize")}
            className="relative bg-line outline-none transition-colors duration-150 after:absolute hover:bg-accent focus-visible:bg-accent data-dragging:bg-accent data-[orientation=horizontal]:w-px data-[orientation=horizontal]:after:inset-y-0 data-[orientation=horizontal]:after:-inset-x-1.5 data-[orientation=vertical]:h-px data-[orientation=vertical]:after:inset-x-0 data-[orientation=vertical]:after:-inset-y-1.5"
          />
          <ResizablePanel minSize={wide ? 40 : 30} className="flex min-h-0 min-w-0 flex-col">
            {fieldsPane}
          </ResizablePanel>
        </Resizable>
      </TabsPanel>
    </Tabs>
  );
}
