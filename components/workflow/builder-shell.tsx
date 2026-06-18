"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  AlertCircle,
  User,
  CalendarDays,
} from "lucide-react";
import { DocumentsSection } from "./documents-section";
import { RulesPanel } from "./rules-panel";
import { BuilderStepNav, stepComplete, type BuilderStep } from "./builder/step-nav";
import { BuilderStepFooter } from "./builder/builder-step-footer";
import { TestDeployStep } from "./builder/test-run-panel";
import { BuilderTopbar } from "./builder/builder-topbar";
import { BuilderMobileSteps } from "./builder/builder-mobile-steps";
import { WorkflowNameGate } from "./builder/workflow-name-gate";
import { useBuilderWorkflow } from "./builder/use-builder-workflow";
import type { Workflow, RuleTemplate } from "@/lib/types";

type BuilderMode = "new" | "edit";

function BuilderShellCore({
  workflow,
  mode,
  ruleLibrary,
}: {
  workflow: Workflow;
  mode: BuilderMode;
  ruleLibrary?: RuleTemplate[];
}) {
  const tSteps = useTranslations("workflows.builder.steps");
  const isNew = mode === "new";
  const [nameConfirmed, setNameConfirmed] = useState(() => !isNew || workflow.name.trim().length > 0);

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
    saving,
    activeWorkflowId,
    testSession,
    patchTestSession,
    handleDeploy,
    handleSaveDraft,
    persistWorkflow,
  } = useBuilderWorkflow(workflow, mode);

  const schemaReady = stepComplete(0, documents, rules);
  const showNameGate = isNew && !nameConfirmed;

  return (
    <div className="flex flex-col page-enter" style={{ height: "calc(100vh - 64px)" }}>
      <BuilderTopbar
        name={name}
        deployed={deployed}
        saving={saving}
        schemaReady={schemaReady}
        onNameChange={setName}
        onSaveDraft={() => handleSaveDraft()}
        onDeploy={handleDeploy}
      />

      {showNameGate ? (
        <WorkflowNameGate
          name={name}
          onNameChange={setName}
          onContinue={() => {
            if (name.trim()) setNameConfirmed(true);
          }}
        />
      ) : (
        <>
      <div className="flex flex-1 overflow-hidden min-h-0">
        <aside className="hidden md:flex w-52 xl:w-60 border-r border-border/80 flex-col gap-0 p-3 shrink-0 overflow-y-auto bg-surface-container-lowest/80 backdrop-blur-sm">
          <BuilderStepNav
            current={step}
            documents={documents}
            rules={rules}
            onChange={setStep}
            tSteps={tSteps}
            testHasResults={!!testSession.result}
          />

          <div className="mt-6 border-t border-border pt-4 space-y-2.5 px-1">
            <div className="flex items-center gap-2 text-[11px] text-on-surface-variant">
              <User className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{workflow.owner}</span>
            </div>
            {workflow.lastRun ? (
              <div className="flex items-center gap-2 text-[11px] text-on-surface-variant">
                <CalendarDays className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">{workflow.lastRun}</span>
              </div>
            ) : null}
            {!schemaReady && step > 0 ? (
              <div className="flex items-start gap-1.5 text-[11px] text-warning">
                <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{tSteps("schemaIncomplete")}</span>
              </div>
            ) : null}
          </div>
        </aside>

        <main className="flex flex-1 flex-col min-w-0 overflow-hidden">
          <div key={step} className="flex-1 overflow-y-auto p-5 md:p-6 lg:p-8 min-w-0">
            <div className="mx-auto w-full max-w-4xl page-enter min-w-0">
              {step === 0 ? (
                <DocumentsSection documents={documents} onChange={setDocuments} />
              ) : null}
              {step === 1 ? (
                <RulesPanel
                  rules={rules}
                  documents={documents}
                  onChange={setRules}
                  initialRuleLibrary={ruleLibrary}
                />
              ) : null}
              {step === 2 ? (
                <TestDeployStep
                  workflowId={activeWorkflowId}
                  name={name || workflow.name}
                  apiKey={apiKey}
                  apiKeyHint={workflow.apiKeyHint}
                  documents={documents}
                  rules={rules}
                  deployed={deployed}
                  onDeploy={handleDeploy}
                  onBeforeRun={() =>
                    persistWorkflow({ navigate: false, toastOnSuccess: false })
                  }
                  testSession={testSession}
                  onTestSessionChange={patchTestSession}
                />
              ) : null}
            </div>
          </div>

          <BuilderStepFooter
            step={step}
            documents={documents}
            rules={rules}
            onBack={() => setStep((step - 1) as BuilderStep)}
            onContinue={() => setStep((step + 1) as BuilderStep)}
          />
        </main>
      </div>

      <BuilderMobileSteps
        step={step}
        documents={documents}
        rules={rules}
        onChange={setStep}
      />
        </>
      )}
    </div>
  );
}

/** Create a blank workflow in the builder (navigates on first save). */
export function NewWorkflowBuilder({ workflow }: { workflow: Workflow }) {
  return <BuilderShellCore key={workflow.id} workflow={workflow} mode="new" />;
}

/** Edit an existing workflow with optional server-fetched rule library. */
export function EditWorkflowBuilder({
  workflow,
  ruleLibrary,
}: {
  workflow: Workflow;
  ruleLibrary?: RuleTemplate[];
}) {
  return (
    <BuilderShellCore
      key={workflow.id}
      workflow={workflow}
      mode="edit"
      ruleLibrary={ruleLibrary}
    />
  );
}
