"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { EASE_OUT } from "@/lib/motion";
import { fieldKey } from "@/lib/rules/field-key";
import type { Workflow } from "@/lib/types";
import { BuilderTopbar } from "./builder/builder-topbar";
import { NameWorkflowDialog } from "./builder/name-workflow-dialog";
import { type BuilderStep, BuilderSteps, STEP_KEYS, stepComplete } from "./builder/step-nav";
import { TestDeployStep } from "./builder/test-run-panel";
import { useBuilderWorkflow } from "./builder/use-builder-workflow";
import { useTestRun } from "./builder/use-test-run";
import { ExtractionWorkbench } from "./extraction/extraction-workbench";
import { RulesPanel } from "./rules/rules-panel";

type BuilderMode = "new" | "edit";

function BuilderShellCore({ workflow, mode }: { workflow: Workflow; mode: BuilderMode }) {
  const t = useTranslations("workflows.builder.steps");
  const router = useRouter();
  const [naming, setNaming] = useState(mode === "new");
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
  const test = useTestRun({
    documents,
    rules,
    session: testSession,
    onSessionChange: setTestSession,
    saveForTestRun,
  });
  const schemaReady = stepComplete(0, documents, rules);

  const switchFieldToNumber = (fieldName: string) => {
    const target = fieldKey(fieldName);
    const multi = documents.length > 1;
    setDocuments(
      documents.map((doc) => ({
        ...doc,
        schema: doc.schema.map((field) => {
          const qualified = multi ? `${doc.documentType}.${field.name}` : field.name;
          if (fieldKey(qualified) === target || fieldKey(field.name) === target) {
            return { ...field, templateType: "number" };
          }
          if (field.templateType === "object") {
            return {
              ...field,
              children: field.children.map((child) => {
                const nested = `${field.name}.${child.name}`;
                const qualifiedNested = multi ? `${doc.documentType}.${nested}` : nested;
                if (fieldKey(qualifiedNested) === target || fieldKey(nested) === target) {
                  return { ...child, templateType: "number" };
                }
                return child;
              }),
            };
          }
          return field;
        }),
      }))
    );
  };

  return (
    <div className="flex h-full flex-col">
      <NameWorkflowDialog
        open={naming}
        onCancel={() => router.push("/workflows")}
        onStart={(names) => {
          setName(names.workflow);
          setDocuments(
            documents.map((doc, i) => (i === 0 ? { ...doc, documentType: names.document } : doc))
          );
          setNaming(false);
        }}
      />
      <BuilderTopbar
        name={name}
        deployed={deployed}
        sync={sync}
        saveState={saveState}
        test={test}
        onNameChange={setName}
        onSaveDraft={() => handleSaveDraft()}
        onOpenTest={() => {
          if (schemaReady) setStep(2);
        }}
        steps={
          <BuilderSteps
            step={step}
            documents={documents}
            rules={rules}
            deployed={deployed}
            onStepChange={setStep}
          />
        }
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
          <section aria-label={t(STEP_KEYS[step])} className="h-full">
            {step === 0 ? (
              <ExtractionWorkbench documents={documents} test={test} onChange={setDocuments} />
            ) : (
              <div className="h-full overflow-y-auto overscroll-contain">
                <div className="mx-auto w-full max-w-[1160px] px-4 py-6 md:px-8">
                  {step === 1 ? (
                    <fieldset disabled={!canEdit} className="contents">
                      <RulesPanel
                        rules={rules}
                        documents={documents}
                        results={
                          test.run.phase === "done" ? test.run.result.ruleResults : undefined
                        }
                        onSwitchFieldToNumber={canEdit ? switchFieldToNumber : undefined}
                        onChange={setRules}
                      />
                    </fieldset>
                  ) : (
                    <TestDeployStep
                      workflowId={workflow.id}
                      name={name || workflow.name}
                      apiKey={apiKey}
                      apiKeyHint={workflow.apiKeyHint ?? undefined}
                      documents={documents}
                      deployed={deployed}
                      sync={sync}
                      test={test}
                      onDeploy={handleDeploy}
                    />
                  )}
                </div>
              </div>
            )}
          </section>
        </motion.div>
      </AnimatePresence>
      <footer className="flex h-14 shrink-0 items-center justify-between gap-3 border-t border-line bg-panel px-4 md:px-6">
        {step > 0 ? (
          <Button variant="ghost" size="md" onClick={() => setStep((step - 1) as BuilderStep)}>
            <ArrowLeft />
            {t("backTo", { step: t(STEP_KEYS[step - 1]) })}
          </Button>
        ) : (
          <span />
        )}
        {step === 1 && !schemaReady ? (
          <p className="hidden text-xs text-ink-3 sm:block">{t("continueBlockedSchema")}</p>
        ) : null}
        {step < 2 ? (
          <Button
            variant="primary"
            size="md"
            disabled={step === 1 && !schemaReady}
            title={step === 1 && !schemaReady ? t("continueBlockedSchema") : undefined}
            onClick={() => setStep((step + 1) as BuilderStep)}
          >
            {t("nextTo", { step: t(STEP_KEYS[step + 1]) })}
            <ArrowRight />
          </Button>
        ) : (
          <span />
        )}
      </footer>
    </div>
  );
}

export function NewWorkflowBuilder({ workflow }: { workflow: Workflow }) {
  return <BuilderShellCore key={workflow.id} workflow={workflow} mode="new" />;
}

export function EditWorkflowBuilder({ workflow }: { workflow: Workflow }) {
  return <BuilderShellCore key={workflow.id} workflow={workflow} mode="edit" />;
}
