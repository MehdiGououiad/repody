"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { browserApi } from "@/lib/api/openapi-client";
import { syncRuleBodies } from "@/lib/rules/sync-rules";
import { getRuleIssues } from "@/lib/rules/rule-validation";
import { useUnsavedChangesWarning } from "@/lib/hooks/use-unsaved-changes-warning";
import { emptyTestSession, type TestSessionState } from "@/components/workflow/builder/test-run-panel";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import type { DocumentDef, Workflow, WorkflowRule } from "@/lib/types";

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
  const [saving, setSaving] = useState(false);
  const [activeWorkflowId, setActiveWorkflowId] = useState(workflow.id);
  const [testSession, setTestSession] = useState<TestSessionState>(emptyTestSession);
  const [savedFingerprint, setSavedFingerprint] = useState(() =>
    JSON.stringify({
      name: workflow.name,
      documents: workflow.documents,
      rules: syncRuleBodies(workflow.rules),
      defaultLlmModel: workflow.defaultLlmModel ?? null,
    })
  );

  const dirty = useMemo(
    () =>
      JSON.stringify({
        name,
        documents,
        rules: syncRuleBodies(rules),
      }) !== savedFingerprint,
    [name, documents, rules, savedFingerprint]
  );

  useUnsavedChangesWarning(dirty);

  const patchTestSession = (patch: Partial<TestSessionState>) =>
    setTestSession((prev) => ({ ...prev, ...patch }));

  const buildPayload = (idOverride?: string): Workflow => ({
    id: idOverride ?? (activeWorkflowId === "new" ? workflow.id : activeWorkflowId),
    name: name || workflow.name,
    description: workflow.description,
    status: deployed ? "active" : "draft",
    owner: workflow.owner,
    lastRun: workflow.lastRun,
    successRate: workflow.successRate,
    totalRuns: workflow.totalRuns,
    documents,
    rules: syncRuleBodies(rules),
    deployedAt: workflow.deployedAt,
    apiKey: apiKey || workflow.apiKey,
    defaultLlmModel: workflow.defaultLlmModel ?? null,
  });

  const persistWorkflow = async (options?: {
    navigate?: boolean;
    toastOnSuccess?: boolean;
  }): Promise<string> => {
    const id = activeWorkflowId === "new" ? workflow.id : activeWorkflowId;
    const payload = buildPayload(id);
    if (!payload.name?.trim()) {
      throw new Error(t("toasts.nameRequired"));
    }
    for (const rule of payload.rules) {
      const selectedDocuments = payload.documents.filter((document) =>
        rule.appliesTo.includes(document.id)
      );
      const multipleDocuments = selectedDocuments.length > 1;
      const availableFields = selectedDocuments.flatMap((document) =>
        document.schema
          .filter((field) => field.name.trim())
          .map((field) => {
            const fieldName = field.name.trim().toLowerCase().replace(/\s+/g, "_");
            if (!multipleDocuments) return fieldName;
            const documentName = document.documentType
              .trim()
              .toLowerCase()
              .replace(/\s+/g, "_");
            return `${documentName}.${fieldName}`;
          })
      );
      const issues = getRuleIssues(
        rule,
        rule.kind === "llm" ? availableFields : undefined
      );
      if (issues.length) {
        const label = rule.name?.trim() || rule.id;
        throw new Error(`${label}: ${issues[0]}`);
      }
    }
    const { error, response } = await browserApi.PUT("/v1/workflows/{workflow_id}", {
      params: { path: { workflow_id: id } },
      body: payload as never,
    });
    if (error || !response.ok) {
      throw new Error(`Save failed: HTTP ${response.status}`);
    }
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
      JSON.stringify({
        name: payload.name,
        documents: payload.documents,
        rules: payload.rules,
        defaultLlmModel: payload.defaultLlmModel ?? null,
      })
    );
    return id;
  };

  const handleDeploy = async () => {
    try {
      const id = await persistWorkflow({ navigate: false, toastOnSuccess: false });
      const { data, error, response } = await browserApi.POST("/v1/workflows/{workflow_id}/deploy", {
        params: { path: { workflow_id: id } },
        body: {},
      });
      if (error || !response.ok || !data) {
        throw new Error(`Deploy failed: HTTP ${response.status}`);
      }
      const res = data as { workflow: Workflow };
      setDeployed(true);
      const revealed = res.workflow.apiKey ?? apiKey;
      setApiKey(revealed);
      rememberApiKey(id, revealed);
      setStep(2);
      setSavedFingerprint(
        JSON.stringify({
          name: name || workflow.name,
          documents,
          rules: syncRuleBodies(rules),
        })
      );
      toast.success(t("toasts.deployed"), {
        description: t("toasts.deployedDetail"),
      });
    } catch {
      toast.error(tCommon("saveFailed"));
    }
  };

  const handleSaveDraft = async (toastOnSuccess = true) => {
    setSaving(true);
    try {
      await persistWorkflow({ navigate: isNew, toastOnSuccess });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : tCommon("saveFailed"));
    } finally {
      setSaving(false);
    }
  };

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
    saving,
    activeWorkflowId,
    testSession,
    patchTestSession,
    handleDeploy,
    handleSaveDraft,
    persistWorkflow,
  };
}
