"use client";

import { AnimatePresence, motion } from "motion/react";
import { Tabs, TabsPanel } from "@/components/ui/tabs";
import { useRun } from "@/lib/api/runs";
import { EASE_OUT } from "@/lib/motion";
import type { Workflow } from "@/lib/types";
import { BuilderTopbar } from "./builder/builder-topbar";
import { type BuilderStep, BuilderTabs, STEP_VALUES, stepComplete } from "./builder/step-nav";
import { PublishStep } from "./builder/test-run-panel";
import { useBuilderWorkflow } from "./builder/use-builder-workflow";
import { ExtractionWorkbench } from "./extraction/extraction-workbench";
import { RulesPanel } from "./rules/rules-panel";

type BuilderMode = "new" | "edit";

function BuilderShellCore({ workflow, mode }: { workflow: Workflow; mode: BuilderMode }) {
  const {
    step,
    setStep,
    name,
    setName,
    documents,
    setDocuments,
    rules,
    setRules,
    canEdit,
    deployed,
    apiKey,
    sync,
    saveState,
    testSession,
    setTestSession,
    handleDeploy,
    handleSaveDraft,
    saveForTestRun,
  } = useBuilderWorkflow(workflow, mode);
  const run = useRun(testSession.runId);

  return (
    <Tabs
      value={STEP_VALUES[step]}
      onValueChange={(value) => {
        const next = STEP_VALUES.indexOf(value as (typeof STEP_VALUES)[number]);
        if (next >= 0) setStep(next as BuilderStep);
      }}
      className="flex h-full flex-col"
    >
      <BuilderTopbar
        name={name}
        deployed={deployed}
        sync={sync}
        saveState={saveState}
        schemaReady={stepComplete(0, documents, rules)}
        onNameChange={setName}
        onSaveDraft={() => handleSaveDraft()}
        onDeploy={handleDeploy}
        steps={<BuilderTabs documents={documents} rules={rules} done={deployed} />}
      />
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, transition: { duration: 0.08 } }}
          transition={{ duration: 0.18, ease: EASE_OUT }}
          className="min-h-0 flex-1"
        >
          <TabsPanel value={STEP_VALUES[step]} className="h-full">
            {step === 0 ? (
              <ExtractionWorkbench
                documents={documents}
                rules={rules}
                onChange={setDocuments}
                session={testSession}
                onSessionChange={setTestSession}
                saveForTestRun={saveForTestRun}
              />
            ) : (
              <div className="h-full overflow-y-auto overscroll-contain">
                <div className="mx-auto w-full max-w-[1080px] px-4 py-6 md:px-8">
                  {step === 1 ? (
                    <fieldset disabled={!canEdit} className="contents">
                      <RulesPanel
                        rules={rules}
                        documents={documents}
                        results={run.phase === "done" ? run.result.ruleResults : undefined}
                        onChange={setRules}
                      />
                    </fieldset>
                  ) : (
                    <PublishStep
                      workflowId={workflow.id}
                      name={name || workflow.name}
                      apiKey={apiKey}
                      apiKeyHint={workflow.apiKeyHint ?? undefined}
                      documents={documents}
                      deployed={deployed}
                      sync={sync}
                      run={run}
                      onDeploy={handleDeploy}
                    />
                  )}
                </div>
              </div>
            )}
          </TabsPanel>
        </motion.div>
      </AnimatePresence>
    </Tabs>
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
