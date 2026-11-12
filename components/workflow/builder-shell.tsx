"use client";

import { ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Workflow } from "@/lib/types";
import { BuilderTopbar } from "./builder/builder-topbar";
import { type BuilderStep, BuilderTabs, stepBlocked, stepComplete } from "./builder/step-nav";
import { TestDeployStep } from "./builder/test-run-panel";
import { useBuilderWorkflow } from "./builder/use-builder-workflow";
import { WorkflowNameGate } from "./builder/workflow-name-gate";
import { DocumentsSection } from "./documents/documents-section";
import { RulesPanel } from "./rules/rules-panel";

type BuilderMode = "new" | "edit";

function BuilderShellCore({ workflow, mode }: { workflow: Workflow; mode: BuilderMode }) {
  const tSteps = useTranslations("workflows.builder.steps");
  const isNew = mode === "new";
  const [nameConfirmed, setNameConfirmed] = useState(
    () => !isNew || workflow.name.trim().length > 0
  );
  const {
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
    testSession,
    setTestSession,
    handleDeploy,
    handleSaveDraft,
    saveForTestRun,
  } = useBuilderWorkflow(workflow, mode);
  const schemaReady = stepComplete(0, documents, rules);
  const next = (step + 1) as BuilderStep;

  return (
    <div className="flex h-full flex-col">
      <BuilderTopbar
        name={name}
        deployed={deployed}
        sync={sync}
        schemaReady={schemaReady}
        onNameChange={setName}
        onSaveDraft={() => handleSaveDraft()}
        onDeploy={handleDeploy}
      />
      {isNew && !nameConfirmed ? (
        <WorkflowNameGate
          name={name}
          onNameChange={setName}
          onContinue={() => {
            if (name.trim()) setNameConfirmed(true);
          }}
        />
      ) : (
        <>
          <BuilderTabs
            current={step}
            documents={documents}
            rules={rules}
            tested={testSession.runId !== null}
            onChange={setStep}
          />
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            <div className="mx-auto w-full max-w-[1100px] px-4 py-6 md:px-8 md:py-8">
              {step === 0 ? (
                <DocumentsSection documents={documents} onChange={setDocuments} />
              ) : null}
              {step === 1 ? (
                <RulesPanel rules={rules} documents={documents} onChange={setRules} />
              ) : null}
              {step === 2 ? (
                <TestDeployStep
                  workflowId={workflow.id}
                  name={name || workflow.name}
                  apiKey={apiKey}
                  apiKeyHint={workflow.apiKeyHint ?? undefined}
                  documents={documents}
                  rules={rules}
                  deployed={deployed}
                  sync={sync}
                  onDeploy={handleDeploy}
                  saveForTestRun={saveForTestRun}
                  testSession={testSession}
                  onTestSessionChange={setTestSession}
                />
              ) : null}

              {step < 2 ? (
                <div className="mt-10 flex flex-wrap items-center justify-end gap-3 border-t border-line pt-5">
                  {stepBlocked(next, documents, rules) ? (
                    <p className="text-sm text-ink-3">{tSteps("continueBlockedSchema")}</p>
                  ) : step === 1 && !stepComplete(1, documents, rules) ? (
                    <p className="text-sm text-ink-3">{tSteps("continueRulesOptional")}</p>
                  ) : null}
                  <Button
                    variant="secondary"
                    disabled={stepBlocked(next, documents, rules)}
                    onClick={() => setStep(next)}
                  >
                    {tSteps(step === 0 ? "continueToRules" : "continueToTest")}
                    <ArrowRight />
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/** Create a blank workflow in the builder (navigates on first save). */
export function NewWorkflowBuilder({ workflow }: { workflow: Workflow }) {
  return <BuilderShellCore key={workflow.id} workflow={workflow} mode="new" />;
}

/** Edit an existing workflow. */
export function EditWorkflowBuilder({ workflow }: { workflow: Workflow }) {
  return <BuilderShellCore key={workflow.id} workflow={workflow} mode="edit" />;
}
