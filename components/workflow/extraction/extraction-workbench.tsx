"use client";

import { useMutation } from "@tanstack/react-query";
import { Button as ButtonPrimitive } from "@ui-sdk/react/button";
import { Resizable, ResizableHandle, ResizablePanel } from "@ui-sdk/react/resizable";
import { useShortcut, useShortcutHint } from "@ui-sdk/react/shortcuts";
import { FileUp, Play, Plus, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useCan } from "@/components/auth/access-context";
import { Gate } from "@/components/auth/gate";
import { usePlayground } from "@/components/playground/playground";
import { DocChip } from "@/components/shared/doc-chip";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import type { TestSession } from "@/components/workflow/builder/use-builder-workflow";
import { DocumentCard } from "@/components/workflow/documents/document-card";
import type { FieldResult } from "@/components/workflow/documents/schema-table";
import { RunErrorAlert } from "@/components/workflow/run-error-alert";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import { startRun, useRun } from "@/lib/api/runs";
import { useMediaQuery } from "@/lib/hooks/use-media-query";
import { openCredits } from "@/lib/playground/credits";
import { errorMessage } from "@/lib/query/get-query-client";
import { fieldKey } from "@/lib/rules/field-key";
import type { DocumentDef, SchemaField, WorkflowRule } from "@/lib/types";
import { cn } from "@/lib/utils";
import { newDocument } from "@/lib/workflow/new-items";

const ACCEPT = {
  "application/pdf": [".pdf"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/webp": [".webp"],
};

const signature = (field: SchemaField) =>
  `${field.name}|${field.templateType}|${field.description}`;

/** The sample: dropped once, then shown as the browser renders it (PDF viewer or image). */
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
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: ACCEPT,
    maxFiles: 1,
    multiple: false,
    noClick: Boolean(file),
    // The visible buttons open the picker; the drop area itself is not a second tab stop.
    noKeyboard: true,
    onDropAccepted: ([accepted]) => onFileChange(accepted ?? null),
  });

  return (
    <div
      {...getRootProps({
        className: "relative flex h-full min-h-0 flex-col bg-canvas outline-none",
      })}
    >
      <input {...getInputProps()} aria-hidden />
      {file && url ? (
        <>
          <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line px-3">
            <span className="min-w-0 flex-1 truncate text-[13px] text-ink-2">{file.name}</span>
            <Button variant="ghost" size="xs" onClick={open}>
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
              {/* biome-ignore lint/performance/noImgElement: a local sample, shown as dropped. */}
              <img
                src={url}
                alt={file.name}
                className="mx-auto h-auto max-w-full rounded-md shadow-[0_0_0_1px_var(--line)]"
              />
            </div>
          )}
        </>
      ) : (
        <ButtonPrimitive
          onClick={open}
          className={cn(
            "m-auto flex aspect-[1/1.2] w-[min(320px,calc(100%-2rem))] cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-line-strong bg-panel px-6 text-center transition-[border-color,background-color,scale] duration-150 hover:border-accent hover:bg-accent-wash/40 active:scale-[0.99]",
            isDragActive && "border-accent bg-accent-wash"
          )}
        >
          <motion.span
            animate={isDragActive ? { y: -4, scale: 1.06 } : { y: 0, scale: 1 }}
            transition={{ type: "spring", duration: 0.3, bounce: 0 }}
            className="flex size-10 items-center justify-center rounded-full bg-panel text-ink-3 shadow-[0_0_0_1px_var(--line)]"
          >
            <FileUp className="size-4" aria-hidden />
          </motion.span>
          <span className="text-[13px] font-medium text-ink">{t("samplePrompt")}</span>
          <span className="max-w-64 text-xs text-ink-3">{t("sampleHint")}</span>
        </ButtonPrimitive>
      )}
      {isDragActive && file ? (
        <div className="pointer-events-none absolute inset-2 rounded-xl border-2 border-dashed border-accent bg-accent-wash" />
      ) : null}
    </div>
  );
}

/**
 * Extraction, as a workbench: a sample of each document on the left, its fields on the right
 * with the value the model found in the sample. Extract (⌘↵) runs the unsaved draft.
 */
export function ExtractionWorkbench({
  documents,
  rules,
  onChange,
  session,
  onSessionChange,
  saveForTestRun,
}: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  onChange: (documents: DocumentDef[]) => void;
  session: TestSession;
  onSessionChange: (session: TestSession) => void;
  saveForTestRun: () => Promise<string>;
}) {
  const t = useTranslations("workflows.builder.workbench");
  const tDoc = useTranslations("workflows.builder.docSource");
  const tTest = useTranslations("workflows.builder.test");
  const [activeId, setActiveId] = useState(documents[0]?.id);
  const active = documents.find((d) => d.id === activeId) ?? documents[0];
  const activeIndex = documents.indexOf(active);
  const [snapshot, setSnapshot] = useState<Map<string, string>>(new Map());
  const extractHint = useShortcutHint("mod+enter");
  const wide = useMediaQuery("(min-width: 1024px)");

  const start = useMutation({
    mutationFn: async () =>
      startRun({ workflowId: await saveForTestRun(), documents, rules, files: session.files }),
    onMutate: () => {
      setSnapshot(
        new Map(documents.flatMap((d) => d.schema.map((f) => [f.id, signature(f)] as const)))
      );
      onSessionChange({ ...session, runId: null });
    },
    onSuccess: ({ runId }) => onSessionChange({ ...session, runId }),
  });
  const run = useRun(session.runId);
  const busy = start.isPending || run.phase === "running";
  const canEdit = useCan("workflow:write");
  const canRun = useCan("run:execute");
  const canExtract = canEdit && canRun && Object.keys(session.files).length > 0 && !busy;
  // The playground configures but does not extract: it asks for credits instead.
  const playground = usePlayground();
  const extract = () => (playground ? openCredits() : start.mutate());
  useShortcut("mod+enter", extract, {
    allowInInput: true,
    when: () => canExtract,
    description: t("extract"),
  });

  const results = useMemo(() => {
    const byDoc = new Map<string, Map<string, FieldResult>>();
    if (run.phase !== "done") return byDoc;
    for (const doc of documents) {
      const found = run.result.documents.find(
        (d) => d.documentType.trim() === doc.documentType.trim()
      );
      if (!found) continue;
      byDoc.set(
        doc.id,
        new Map(
          found.fields.map((f) => [fieldKey(f.key), { extracted: f.extracted, value: f.value }])
        )
      );
    }
    return byDoc;
  }, [run, documents]);
  const stale = new Set(
    active?.schema
      .filter((f) => snapshot.size && snapshot.get(f.id) !== signature(f))
      .map((f) => f.id) ?? []
  );
  const activeResults = active ? results.get(active.id) : undefined;
  const found = activeResults ? [...activeResults.values()].filter((r) => r.extracted).length : 0;

  if (!active) return null;
  const updateDoc = (patch: Partial<DocumentDef>) =>
    onChange(documents.map((d) => (d.id === active.id ? { ...d, ...patch } : d)));
  const setFile = (file: File | null) => {
    const files = { ...session.files };
    if (file) files[active.id] = file;
    else delete files[active.id];
    onSessionChange({ ...session, files });
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
          <div className="flex shrink-0 items-center gap-2">
            {activeResults ? (
              <span className="hidden text-xs tabular-nums text-ink-3 sm:inline">
                {t("found", { found, total: activeResults.size })}
              </span>
            ) : null}
            <Gate permission="run:execute">
              <Button
                variant="primary"
                size="sm"
                onClick={extract}
                disabled={!canExtract}
                title={Object.keys(session.files).length ? t("extractHint") : t("needSample")}
              >
                <Play />
                {busy ? t("extracting") : t("extract")}
                <Kbd className="ms-0.5">{extractHint.text}</Kbd>
              </Button>
            </Gate>
          </div>
        }
      />
      {start.isError ? (
        <div className="border-t border-line p-3">
          <RunErrorAlert
            title={tTest("errorTitle")}
            message={errorMessage(start.error, tTest("errorTitle"))}
          />
        </div>
      ) : null}
      {run.phase === "failed" ? (
        <div className="border-t border-line p-3">
          <RunErrorAlert title={tTest("errorTitle")} message={run.error} runId={session.runId} />
        </div>
      ) : null}
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
              {session.files[doc.id] ? (
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
            className="min-h-0 min-w-0"
          >
            <SamplePane key={active.id} file={session.files[active.id]} onFileChange={setFile} />
          </ResizablePanel>
          <ResizableHandle
            aria-label={t("resize")}
            className="relative bg-line outline-none transition-colors duration-150 after:absolute hover:bg-accent focus-visible:bg-accent data-dragging:bg-accent data-[orientation=horizontal]:w-px data-[orientation=horizontal]:after:inset-y-0 data-[orientation=horizontal]:after:-inset-x-1.5 data-[orientation=vertical]:h-px data-[orientation=vertical]:after:inset-x-0 data-[orientation=vertical]:after:-inset-y-1.5"
          />
          <ResizablePanel minSize={wide ? 40 : 30} className="flex min-h-0 min-w-0 flex-col">
            {fieldsPane}
          </ResizablePanel>
        </Resizable>

        <AnimatePresence>
          {run.phase === "running" && run.progress ? (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12, transition: { duration: 0.15 } }}
              transition={{ type: "spring", duration: 0.32, bounce: 0 }}
              className="absolute end-4 bottom-4 z-20 w-[min(380px,calc(100%-2rem))] rounded-xl bg-overlay p-4 shadow-pop"
            >
              <RunProgressSteps progress={run.progress} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </TabsPanel>
    </Tabs>
  );
}
