"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  emptyTestSession,
  type TestRun,
  type TestSessionState,
} from "@/components/workflow/builder/test-run-session";
import { browserApi, unwrap } from "@/lib/api/openapi-client";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import { useUnsavedChangesWarning } from "@/lib/hooks/use-unsaved-changes-warning";
import type { DocumentDef, Workflow, WorkflowRule } from "@/lib/types";
import { workflowDraftFingerprint } from "@/lib/workflow/draft-fingerprint";

function readStoredApiKey(workflowId: string, fromWorkflow?: string | null): string {
  if (isFullWorkflowApiKey(fromWorkflow)) return fromWorkflow;
  if (typeof sessionStorage === "undefined") return "";
  const stored = sessionStorage.getItem(`workflow-api-key:${workflowId}`);
  return isFullWorkflowApiKey(stored) ? stored : "";
}

function rememberApiKey(workflowId: string, key: string | null | undefined) {
  if (typeof sessionStorage === "undefined" || !isFullWorkflowApiKey(key)) return;
  sessionStorage.setItem(`workflow-api-key:${workflowId}`, key);
}

/**
 * What the builder is sending to the server: one thing at a time, so a deploy never races a
 * save and a double click never issues two API keys. See docs/LIFECYCLES.md.
 */
export type BuilderSync = "idle" | "saving" | "deploying";

export function useBuilderWorkflow(workflow: Workflow, mode: "new" | "edit" = "edit") {
  const isNew = mode === "new";
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [step, setStep] = useState<0 | 1 | 2>(0);
  const [name, setName] = useState(workflow.name);
  const [documents, setDocuments] = useState<DocumentDef[]>(workflow.documents);
  const [rules, setRules] = useState<WorkflowRule[]>(workflow.rules);
  const [deployed, setDeployed] = useState(!!workflow.deployedAt);
  const [apiKey, setApiKey] = useState(() => readStoredApiKey(workflow.id, workflow.apiKey));
  const [sync, setSync] = useState<BuilderSync>("idle");
  const [activeWorkflowId, setActiveWorkflowId] = useState(workflow.id);
  const [testSession, setTestSession] = useState<TestSessionState>(emptyTestSession);
  const [savedFingerprint, setSavedFingerprint] = useState(() =>
    workflowDraftFingerprint({
      name: workflow.name,
      documents: workflow.documents,
      rules: workflow.rules,
    })
  );

  const dirty = useMemo(
    () => workflowDraftFingerprint({ name, documents, rules }) !== savedFingerprint,
    [name, documents, rules, savedFingerprint]
  );

  useUnsavedChangesWarning(dirty);

  const patchTestSession = (patch: Partial<TestSessionState>) =>
    setTestSession((prev) => ({ ...prev, ...patch }));
  const setTestRun = (next: SetStateAction<TestRun>) =>
    setTestSession((prev) => ({
      ...prev,
      run: typeof next === "function" ? next(prev.run) : next,
    }));

  const buildPayload = () => ({
    name: name || workflow.name,
    description: workflow.description,
    owner: workflow.owner,
    documents,
    rules,
  });

  const persistWorkflow = async (options?: {
    navigate?: boolean;
    toastOnSuccess?: boolean;
  }): Promise<string> => {
    const id = activeWorkflowId === "new" ? workflow.id : activeWorkflowId;
    const payload = buildPayload();
    if (!payload.name?.trim()) {
      throw new Error(t("toasts.nameRequired"));
    }
    // The API rejects duplicate field names and rules that do not fit the schema (422).
    await unwrap(
      browserApi.PUT("/v1/workflows/{workflow_id}", {
        params: { path: { workflow_id: id } },
        body: payload,
      })
    );
    if (isNew || activeWorkflowId === "new") {
      setActiveWorkflowId(id);
      if (options?.navigate !== false) {
        router.replace(`/workflows/${id}/edit`);
      } else {
        window.history.replaceState(null, "", `/workflows/${id}/edit`);
      }
    }

    if (options?.toastOnSuccess) {
      toast.success(t("toasts.draftSaved"), {
        description: t("toasts.draftSavedDetail"),
      });
    }
    setSavedFingerprint(
      workflowDraftFingerprint({
        name: payload.name,
        documents: payload.documents,
        rules: payload.rules,
      })
    );
    return id;
  };

  const handleDeploy = async () => {
    if (sync !== "idle") return;
    setSync("deploying");
    try {
      const id = await persistWorkflow({ navigate: false, toastOnSuccess: false });
      const data = await unwrap(
        browserApi.POST("/v1/workflows/{workflow_id}/deploy", {
          params: { path: { workflow_id: id } },
        })
      );
      setDeployed(true);
      const revealed = data.apiKey ?? apiKey;
      setApiKey(revealed);
      rememberApiKey(id, revealed);
      setStep(2);
      setSavedFingerprint(
        workflowDraftFingerprint({
          name: name || workflow.name,
          documents,
          rules,
        })
      );
      toast.success(t("toasts.deployed"), {
        description: t("toasts.deployedDetail"),
      });
    } catch {
      toast.error(tCommon("saveFailed"));
    } finally {
      setSync("idle");
    }
  };

  const save = async ({ silent }: { silent: boolean }) => {
    if (sync !== "idle") return;
    setSync("saving");
    try {
      await persistWorkflow({ navigate: !silent && isNew, toastOnSuccess: !silent });
    } catch (e) {
      if (!silent) toast.error(e instanceof Error ? e.message : tCommon("saveFailed"));
    } finally {
      setSync("idle");
    }
  };

  const handleSaveDraft = () => save({ silent: false });

  const saveRef = useRef(save);

  useEffect(() => {
    saveRef.current = save;
  });

  // Autosave an existing workflow 2.5 s after the last edit, when nothing else is in flight.
  useEffect(() => {
    if (!dirty || sync !== "idle" || isNew) return;
    const timer = window.setTimeout(() => void saveRef.current({ silent: true }), 2500);
    return () => window.clearTimeout(timer);
  }, [dirty, sync, isNew, name, documents, rules]);

  return {
    step,
    setStep,
    name,
    setName,
    documents,
    setDocuments,
    rules,
    setRules,
    deployed,
    apiKey,
    sync,
    activeWorkflowId,
    testSession,
    patchTestSession,
    setTestRun,
    handleDeploy,
    handleSaveDraft,
    persistWorkflow,
  };
}
