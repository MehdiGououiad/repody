"use client";

import { useQueryClient } from "@tanstack/react-query";
import { toast } from "@ui-sdk/react/toast";
import { dequal } from "dequal";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useEffectEvent, useState } from "react";
import { usePlayground } from "@/components/playground/playground";
import type { BuilderStep } from "@/components/workflow/builder/step-nav";
import { $api } from "@/lib/api/browser";
import { useUnsavedChangesWarning } from "@/lib/hooks/use-unsaved-changes-warning";
import { openCredits } from "@/lib/playground/credits";
import { errorMessage } from "@/lib/query/get-query-client";
import type { DocumentDef, Workflow, WorkflowRule } from "@/lib/types";

const AUTOSAVE_MS = 2_500;

interface Draft {
  name: string;
  documents: DocumentDef[];
  rules: WorkflowRule[];
}

/**
 * What the builder is sending to the server: one thing at a time, so a deploy never races a
 * save and a double click never issues two API keys. See docs/LIFECYCLES.md.
 */
export type BuilderSync = "idle" | "saving" | "deploying";

/** What the header says about the draft: in flight, on the server, edited, refused, or a
 * playground example (shared: saving makes the visitor's own copy). */
export type SaveState =
  | { kind: "saving" | "deploying" | "saved" | "unsaved" | "example" }
  | { kind: "failed"; reason: string };

/** A builder test run: the files chosen per document (kept across runs) and the last run. */
export type TestSession = { files: Record<string, File>; runId: string | null };

/**
 * The workflow being edited and what the builder does with it: save, autosave, deploy.
 * "Unsaved" is derived, not stored: the draft deeply differs from the last saved draft, so an edit
 * and its undo is not a change, and edits made while a save is in flight stay unsaved.
 */
export function useBuilderWorkflow(workflow: Workflow, mode: "new" | "edit" = "edit") {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const tPlayground = useTranslations("playground");
  const playground = usePlayground();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [draft, setDraft] = useState<Draft>(() => ({
    name: workflow.name,
    documents: workflow.documents,
    rules: workflow.rules,
  }));
  // What the server has: the workflow as loaded, then each saved draft.
  const [saved, setSaved] = useState<Draft>(draft);
  const dirty = !dequal(draft, saved);

  const [step, setStep] = useState<BuilderStep>(0);
  const [persisted, setPersisted] = useState(mode === "edit");
  const [deployed, setDeployed] = useState(Boolean(workflow.deployedAt));
  // The full key is returned once, by deploy; it is never stored (a reload shows the hint).
  const [apiKey, setApiKey] = useState(workflow.apiKey ?? "");
  const [testSession, setTestSession] = useState<TestSession>({ files: {}, runId: null });
  // Why the last save was refused (a rule half written, say), until a save goes through.
  const [saveError, setSaveError] = useState<string | null>(null);

  const saveMutation = $api.useMutation("put", "/v1/workflows/{workflow_id}");
  const deployMutation = $api.useMutation("post", "/v1/workflows/{workflow_id}/deploy");
  const copyMutation = $api.useMutation("post", "/v1/workflows/{workflow_id}/duplicate");
  const sync: BuilderSync = deployMutation.isPending
    ? "deploying"
    : saveMutation.isPending || copyMutation.isPending
      ? "saving"
      : "idle";
  const saveState: SaveState =
    sync !== "idle"
      ? { kind: sync }
      : workflow.readOnly && !dirty
        ? { kind: "example" }
        : !dirty
          ? { kind: "saved" }
          : saveError
            ? { kind: "failed", reason: saveError }
            : { kind: "unsaved" };
  useUnsavedChangesWarning(dirty);

  const update =
    <K extends keyof Draft>(key: K) =>
    (value: Draft[K]) =>
      setDraft((previous) => ({ ...previous, [key]: value }));

  /** Save the draft; the first save of a new workflow moves the URL to its edit page. */
  const persist = async ({ navigate }: { navigate: boolean }): Promise<string> => {
    const snapshot = draft;
    if (!snapshot.name.trim()) throw new Error(t("toasts.nameRequired"));
    await saveMutation.mutateAsync({
      params: { path: { workflow_id: workflow.id } },
      body: { ...snapshot, description: workflow.description, owner: workflow.owner },
    });
    if (!persisted) {
      const href = `/workflows/${workflow.id}/edit`;
      if (navigate) router.replace(href);
      else window.history.replaceState(null, "", href);
    }
    setSaved(snapshot);
    setSaveError(null);
    setPersisted(true);
    void queryClient.invalidateQueries({ queryKey: ["get", "/v1/workflows"] });
    return workflow.id;
  };

  /** A shared example (playground): the visitor's own copy, with their edits, opened. */
  const saveAsCopy = async () => {
    const details = { description: workflow.description, owner: workflow.owner };
    const copy = await copyMutation.mutateAsync({
      params: { path: { workflow_id: workflow.id } },
      body: { name: tPlayground("copyName", { name: draft.name || workflow.name }), ...details },
    });
    await saveMutation.mutateAsync({
      params: { path: { workflow_id: copy.id } },
      body: { ...draft, name: copy.name, ...details },
    });
    void queryClient.invalidateQueries({ queryKey: ["get", "/v1/workflows"] });
    toast.success(tPlayground("copied"));
    router.replace(`/workflows/${copy.id}/edit`);
  };

  const handleSaveDraft = async ({ silent = false } = {}) => {
    if (sync !== "idle") return;
    if (workflow.readOnly && silent) return; // examples are copied on an explicit save
    try {
      if (workflow.readOnly) {
        await saveAsCopy();
        return;
      }
      await persist({ navigate: !silent });
      if (!silent) {
        toast.success(t("toasts.draftSaved"), { description: t("toasts.draftSavedDetail") });
      }
    } catch (error) {
      const reason = errorMessage(error, tCommon("saveFailed"));
      setSaveError(reason);
      if (!silent) toast.error(reason);
    }
  };

  const handleDeploy = async () => {
    if (playground) {
      openCredits(); // the playground does not publish
      return;
    }
    if (sync !== "idle") return;
    try {
      const id = await persist({ navigate: false });
      const result = await deployMutation.mutateAsync({ params: { path: { workflow_id: id } } });
      setDeployed(true);
      setApiKey(result.apiKey ?? "");
      setStep(2);
      toast.success(t("toasts.deployed"), { description: t("toasts.deployedDetail") });
    } catch (error) {
      toast.error(errorMessage(error, tCommon("saveFailed")));
    }
  };

  // Autosave a saved workflow shortly after the last edit, when nothing else is in flight.
  const autosave = useEffectEvent(() => void handleSaveDraft({ silent: true }));
  useEffect(() => {
    if (!persisted || !dirty || sync !== "idle" || workflow.readOnly) return;
    const timer = window.setTimeout(autosave, AUTOSAVE_MS);
    return () => window.clearTimeout(timer);
  }, [persisted, dirty, sync, draft, workflow.readOnly]);

  return {
    step,
    setStep,
    ...draft,
    setName: update("name"),
    setDocuments: update("documents"),
    setRules: update("rules"),
    deployed,
    apiKey,
    sync,
    saveState,
    testSession,
    setTestSession,
    handleDeploy,
    handleSaveDraft,
    /** Save before a test run, so it uses what the builder shows (returns the workflow id). */
    saveForTestRun: () => persist({ navigate: false }),
  };
}
