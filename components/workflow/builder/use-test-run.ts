"use client";

import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useCan } from "@/components/auth/access-context";
import type { TestSession } from "@/components/workflow/builder/use-builder-workflow";
import { startRun, useRun } from "@/lib/api/runs";
import type { DocumentDef, SchemaField, WorkflowRule } from "@/lib/types";

const signature = (field: SchemaField) =>
  `${field.name}|${field.templateType}|${field.description}`;

export function useTestRun({
  documents,
  rules,
  session,
  onSessionChange,
  saveForTestRun,
}: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  session: TestSession;
  onSessionChange: (session: TestSession) => void;
  saveForTestRun: () => Promise<string>;
}) {
  const [snapshot, setSnapshot] = useState<Map<string, string>>(new Map());
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const canEdit = useCan("workflow:write");
  const canRun = useCan("run:execute");

  const start = useMutation({
    mutationFn: async () =>
      startRun({ workflowId: await saveForTestRun(), documents, rules, files: session.files }),
    onMutate: () => {
      setSnapshot(
        new Map(documents.flatMap((d) => d.schema.map((f) => [f.id, signature(f)] as const)))
      );
      setStartedAt(Date.now());
      setElapsedMs(0);
      onSessionChange({ ...session, runId: null });
    },
    onSuccess: ({ runId }) => onSessionChange({ ...session, runId }),
  });
  const run = useRun(session.runId);
  const busy = start.isPending || run.phase === "running";
  const sampleCount = documents.filter((d) => session.files[d.id]).length;

  useEffect(() => {
    if (!busy || startedAt === null) return;
    const tick = () => setElapsedMs(Date.now() - startedAt);
    tick();
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [busy, startedAt]);

  return {
    run,
    runId: session.runId,
    files: session.files,
    starting: start.isPending,
    busy,
    elapsedMs,
    sampleCount,
    canRun: canEdit && canRun,
    ready: canEdit && canRun && sampleCount > 0 && !busy,
    start: () => start.mutate(),
    startError: start.isError ? start.error : null,
    isStale: (field: SchemaField) =>
      snapshot.size > 0 && snapshot.get(field.id) !== signature(field),
    setFile: (docId: string, file: File | null) => {
      const files = { ...session.files };
      if (file) files[docId] = file;
      else delete files[docId];
      onSessionChange({ ...session, files });
    },
    setFiles: (files: Record<string, File>) => onSessionChange({ ...session, files }),
  };
}

export type TestRun = ReturnType<typeof useTestRun>;
